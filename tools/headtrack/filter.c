/* Offline prototype for 2607061716. Hard-float Cortex-M4 ABI.
 * Keep stock motion task, integer peer pose and HID transport operational.
 * Direct quaternion packing is a LAB path: physical iPhone frame/units unverified.
 */
#include <stdint.h>

#define DT (1.0f / 240.0f)
#define RAD 0.017453292519943295f
#define VEC(a) ((volatile float *)(a))
#define INIT (*(volatile uint16_t *)0x833d68)

typedef struct {
    float q[4], bias[3], still, omega[3];
    uint32_t samples;
} State;
static State S;

static float root(float x) {
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x));
    return r;
}

static void multiply(float *out, const float *a, const float *b) {
    float r[4] = {
        a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],
        a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],
        a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],
        a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]
    };
    for (int i=0; i<4; i++) out[i]=r[i];
}

void ht_bias(float ignored, const float *accel, float *gyro, float *bias) {
    (void)ignored;
    if (!INIT) {
        S.still=0;
        S.samples=0;
        for (int i=0; i<3; i++) S.bias[i]=0;
    }
    float an=0, gn=0;
    for (int i=0; i<3; i++) { an+=accel[i]*accel[i]; gn+=gyro[i]*gyro[i]; }
    if (an>.96f*.96f && an<1.04f*1.04f && gn<.75f*.75f) S.still+=DT;
    else S.still=0;
    for (int i=0; i<3; i++) {
        if (S.still>=.5f) S.bias[i]+=(gyro[i]-S.bias[i])*.008298707f;
        bias[i]=S.bias[i];
        gyro[i]-=S.bias[i];
    }
}

void ht_fusion(float gx, float gy, float gz, float ax, float ay, float az, float old_dt) {
    (void)old_dt;
    float norm=root(ax*ax+ay*ay+az*az);
    float a[3]={0, 0, 0};
    if (norm>.01f) { a[0]=ax/norm; a[1]=ay/norm; a[2]=az/norm; }
    if (!INIT) {
        S.q[0]=1; S.q[1]=S.q[2]=S.q[3]=0;
        if (norm>.01f) {
            if (a[2]>.9999f) { S.q[0]=0; S.q[1]=1; }
            else {
                S.q[0]=root((1-a[2])*.5f);
                S.q[1]=-.5f*a[1]/S.q[0];
                S.q[2]=.5f*a[0]/S.q[0];
            }
        }
        INIT=1;
    }
    float w=S.q[0], x=S.q[1], y=S.q[2], z=S.q[3];
    float pred[3]={-2*(x*z-w*y), -2*(w*x+y*z), -(w*w-x*x-y*y+z*z)};
    S.omega[0]=gx*RAD; S.omega[1]=gy*RAD; S.omega[2]=gz*RAD;
    float o[4]={0, S.omega[0], S.omega[1], S.omega[2]};
    if (norm>.9f && norm<1.1f) {
        o[1]+=2*(a[1]*pred[2]-a[2]*pred[1]);
        o[2]+=2*(a[2]*pred[0]-a[0]*pred[2]);
        o[3]+=2*(a[0]*pred[1]-a[1]*pred[0]);
    }
    float delta[4];
    multiply(delta,S.q,o);
    float qnorm=0;
    for (int i=0; i<4; i++) { S.q[i]+=.5f*DT*delta[i]; qnorm+=S.q[i]*S.q[i]; }
    qnorm=root(qnorm);
    for (int i=0; i<4; i++) S.q[i]/=qnorm;
    *VEC(0x82b89c)=S.q[0];
    *VEC(0x82ec68)=S.q[1];
    *VEC(0x82ec6c)=S.q[2];
    *VEC(0x82ec70)=S.q[3];
    S.samples++;
}

static void put16(volatile uint8_t *p, int32_t value) {
    if (value>32767) value=32767;
    if (value< -32767) value= -32767;
    p[0]=(uint8_t)value; p[1]=(uint8_t)(value>>8);
}

/* Demonstrates float-to-wire without Euler loss. Not a calibrated iPhone frame.
 * The existing report sends y,x,z of a quaternion with implicit nonpositive w.
 * Velocity scale 12 counts/dps is inferred from stock's yaw branch, not an Apple spec.
 */
void ht_pack(volatile uint8_t *report) {
    float sign=S.q[0]>0 ? -1.f : 1.f;
    put16(report+0x29,(int32_t)(sign*S.q[2]*32768.f));
    put16(report+0x2b,(int32_t)(sign*S.q[1]*32768.f));
    put16(report+0x2d,(int32_t)(sign*S.q[3]*32768.f));
    for (int i=0; i<3; i++) put16(report+0x2f+2*i,(int32_t)(S.omega[i]*(12.f/RAD)));
}

/* Do not enable on hardware until board->head->HID frame and units are measured. */
void ht_send(uint32_t command) {
    volatile uint8_t *report=*(volatile uint8_t * volatile *)0x833494;
    if (report==(void *)0x836287) ht_pack(report);
    ((void (*)(uint32_t))0xca761d)(command);
}
