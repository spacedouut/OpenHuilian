/* Debug monitor for H3Pro Max3 FIRM 2607061716, built into the FIRM code cave.
 *
 * Adds C0 commands D0-D4 to the SPP command channel. The hook replaces the first instruction of
 * the C0 handler FUN_00c69b3c with a branch to mon_entry: frames `C0 Dx ...` are answered here,
 * everything else runs the stock handler unchanged.
 *
 *   C0 D0                              info   -> "HLMN" ver auth ram len log log_size head cave
 *   C0 D1 addr4 n1                     peek   -> addr4 data  (n = 1/2/4 at an aligned addr is one
 *                                                single-width load, for peripheral registers)
 *   C0 D2 addr4 w1 value4 | bytes...   poke   -> addr4 readback  (w = 1/2/4 one store, 0 = copy)
 *   C0 D3 addr4 [r0 r1 r2 r3]          call   -> r0 r1  (Thumb bit forced on)
 *   C0 D4 op1 [bytes...]               log    op 0 state, 1 clear, 2 append -> magic head size wraps addr
 *
 * Replies are `C0 Dx len status data`; status 0 ok, 1 bad request, 2 locked, 3 unknown command.
 * D2 and D3 answer status 2 until the session has passed the C0 01/02 app handshake (`hl auth`).
 * Peeking an unmapped address can fault the bud, which reboots it.
 *
 * mon_log(ptr, len) appends to a RAM ring that other cave code can use; its address is in the
 * header at the start of the cave. Build with tools/cave/build.py, which writes
 * patches/2607061716/debug-monitor.json. See docs/research/debug-monitor.md.
 */
#include <stdint.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;

#define MON_VERSION 1
#define MON_MAGIC 0x4C4D4C48u /* "HLML" */
#define LOG_SIZE 512
#define PEEK_MAX 200

#define C0_REPLY ((void (*)(u8 *, u32))0x00C69871u) /* FUN_00c69870(buf, len): post a C0 reply */
#define AUTH_OK (*(volatile u8 *)0x008343E8u)         /* set to 1 by C0 02 (FUN_00c69888) */

enum { OK = 0, BAD = 1, LOCKED = 2, UNKNOWN = 3 };

struct mon {
    u32 magic, head, wraps, calls;
    u8 log[LOG_SIZE];
    u8 reply[4 + 4 + PEEK_MAX + 4];
};

/* Not zeroed at boot: lives in heap RAM that cfw.py reserves, so it starts as garbage. */
static struct mon M __attribute__((section(".bss.mon")));

void mon_log(const void *p, u32 n);

struct head {
    u32 magic, version, entry, log, ram, ram_len;
};
extern void mon_entry(void);
__attribute__((section(".text.head"), used)) const struct head mon_head = {
    0x4E4D4C48u /* "HLMN" */, MON_VERSION, (u32)mon_entry, (u32)mon_log, (u32)&M, sizeof(M),
};

__asm__(
    ".syntax unified\n"
    ".cpu cortex-m4\n"
    ".thumb\n"
    ".section .text.entry,\"ax\",%progbits\n"
    ".global mon_entry\n"
    ".type mon_entry, %function\n"
    ".thumb_func\n"
    "mon_entry:\n"
    "  ldrb.w ip, [r0]\n"
    "  cmp ip, #0xC0\n"
    "  bne 1f\n"
    "  ldrb.w ip, [r0, #1]\n"
    "  and ip, ip, #0xF0\n"
    "  cmp ip, #0xD0\n"
    "  bne 1f\n"
    "  push {r4, lr}\n"
    "  bl mon_handle\n"
    "  movs r0, #0\n"
    "  pop {r4, pc}\n"
    "1:\n"
    "  push.w {r4, r5, r6, r7, r8, lr}\n" /* the instruction the hook replaced */
    "  ldr.w ip, =0x00C69B41\n"            /* back into FUN_00c69b3c */
    "  bx ip\n"
    ".ltorg\n");

static u32 rd32(const u8 *p) { return p[0] | p[1] << 8 | p[2] << 16 | (u32)p[3] << 24; }

static void wr32(u8 *p, u32 v)
{
    p[0] = v, p[1] = v >> 8, p[2] = v >> 16, p[3] = v >> 24;
}

static void copy(volatile u8 *d, const volatile u8 *s, u32 n)
{
    while (n--)
        *d++ = *s++;
}

static void init(void)
{
    if (M.magic == MON_MAGIC)
        return;
    M.head = M.wraps = M.calls = 0;
    M.magic = MON_MAGIC;
}

void mon_log(const void *p, u32 n)
{
    const u8 *s = p;
    init();
    while (n--) {
        M.log[M.head % LOG_SIZE] = *s++;
        if (++M.head % LOG_SIZE == 0)
            M.wraps++;
    }
}

static void reply(u8 cmd, u8 status, u32 n)
{
    M.reply[0] = 0xC0;
    M.reply[1] = cmd;
    M.reply[2] = n + 1;
    M.reply[3] = status;
    C0_REPLY(M.reply, n + 4);
}

/* Width-exact access for peripheral registers; byte copy otherwise. */
static void load(u8 *dst, u32 a, u32 n)
{
    if (n == 4 && !(a & 3))
        wr32(dst, *(volatile u32 *)a);
    else if (n == 2 && !(a & 1)) {
        u16 v = *(volatile u16 *)a;
        dst[0] = v, dst[1] = v >> 8;
    } else
        copy(dst, (const volatile u8 *)a, n);
}

static u8 peek(const u8 *f, u32 len, u8 *out, u32 *n)
{
    if (len < 7 || f[6] == 0 || f[6] > PEEK_MAX)
        return BAD;
    u32 a = rd32(f + 2);
    wr32(out, a);
    load(out + 4, a, f[6]);
    *n = 4 + f[6];
    return OK;
}

static u8 poke(const u8 *f, u32 len, u8 *out, u32 *n)
{
    if (len < 8)
        return BAD;
    u32 a = rd32(f + 2), w = f[6];
    if (w == 0) {
        u32 k = len - 7;
        if (k == 0 || k > PEEK_MAX)
            return BAD;
        copy((volatile u8 *)a, f + 7, k);
        w = k;
    } else {
        if (len < 11 || (w != 1 && w != 2 && w != 4) || (a & (w - 1)))
            return BAD;
        u32 v = rd32(f + 7);
        if (w == 4)
            *(volatile u32 *)a = v;
        else if (w == 2)
            *(volatile u16 *)a = v;
        else
            *(volatile u8 *)a = v;
    }
    wr32(out, a);
    load(out + 4, a, w);
    *n = 4 + w;
    return OK;
}

static u8 call(const u8 *f, u32 len, u8 *out, u32 *n)
{
    u32 r[4] = {0, 0, 0, 0};
    if (len < 6 || (len - 6) % 4 || len > 22)
        return BAD;
    for (u32 i = 0; i < (len - 6) / 4; i++)
        r[i] = rd32(f + 6 + 4 * i);
    u64 (*fn)(u32, u32, u32, u32) = (u64(*)(u32, u32, u32, u32))(rd32(f + 2) | 1);
    M.calls++;
    u64 v = fn(r[0], r[1], r[2], r[3]);
    wr32(out, (u32)v);
    wr32(out + 4, (u32)(v >> 32));
    *n = 8;
    return OK;
}

static u8 logcmd(const u8 *f, u32 len, u8 *out, u32 *n)
{
    if (len < 3)
        return BAD;
    if (f[2] == 1)
        M.head = M.wraps = 0;
    else if (f[2] == 2)
        mon_log(f + 3, len - 3);
    else if (f[2] != 0)
        return BAD;
    wr32(out, M.magic);
    wr32(out + 4, M.head);
    wr32(out + 8, LOG_SIZE);
    wr32(out + 12, M.wraps);
    wr32(out + 16, (u32)M.log);
    *n = 20;
    return OK;
}

void mon_handle(const u8 *f, u32 len)
{
    u8 *out = M.reply + 4, st = UNKNOWN;
    u32 n = 0;
    init();
    switch (f[1]) {
    case 0xD0:
        wr32(out, mon_head.magic);
        out[4] = MON_VERSION;
        out[5] = AUTH_OK;
        wr32(out + 6, (u32)&M);
        wr32(out + 10, sizeof(M));
        wr32(out + 14, (u32)M.log);
        wr32(out + 18, LOG_SIZE);
        wr32(out + 22, M.head);
        wr32(out + 26, (u32)&mon_head);
        n = 30, st = OK;
        break;
    case 0xD1:
        st = peek(f, len, out, &n);
        break;
    case 0xD2:
        st = AUTH_OK == 1 ? poke(f, len, out, &n) : LOCKED;
        break;
    case 0xD3:
        st = AUTH_OK == 1 ? call(f, len, out, &n) : LOCKED;
        break;
    case 0xD4:
        st = logcmd(f, len, out, &n);
        break;
    }
    reply(f[1], st, st == OK ? n : 0);
}
