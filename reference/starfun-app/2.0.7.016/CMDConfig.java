package com.sjbt.base.bt;

import android.text.TextUtils;
import cn.hutool.core.util.ByteUtil;
import com.google.common.base.Ascii;
import com.shenju.ota.utils.BtUtils;
import com.sjbt.base.entity.BiuMsgBean;
import com.sjbt.base.log.LogUtil;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Random;
import kotlin.jvm.internal.ShortCompanionObject;

/* loaded from: classes2.dex */
public class CMDConfig {
    public static final String CMD_00 = "00";
    public static final String CMD_01 = "01";
    public static final String CMD_02 = "02";
    public static final String CMD_03 = "03";
    public static final String CMD_04 = "04";
    public static final String CMD_05 = "05";
    public static final String CMD_06 = "06";
    public static final String CMD_07 = "07";
    public static final String CMD_08 = "08";
    public static final String CMD_09 = "09";
    public static final String CMD_0A = "0A";
    public static final String CMD_0B = "0B";
    public static final String CMD_0C = "0C";
    public static final String CMD_0D = "0D";
    public static final String CMD_0E = "0E";
    public static final String CMD_0F = "0F";
    public static final String CMD_10 = "10";
    public static final String CMD_11 = "11";
    public static final String CMD_12 = "12";
    public static final String CMD_13 = "13";
    public static final String CMD_14 = "14";
    public static final String CMD_15 = "15";
    public static final String CMD_16 = "16";
    public static final String CMD_17 = "17";
    public static final String CMD_4 = "04";
    public static final String CMD_50 = "50";
    public static final String CMD_51 = "51";
    public static final String CMD_52 = "52";
    public static final String CMD_53 = "53";
    public static final String CMD_54 = "54";
    public static final String CMD_55 = "55";
    public static final String CMD_56 = "56";
    public static final String CMD_57 = "57";
    public static final String CMD_58 = "58";
    public static final String CMD_59 = "59";
    public static final String CMD_5A = "5A";
    public static final String CMD_5B = "5B";
    public static final String CMD_5C = "5C";
    public static final String CMD_5D = "5D";
    public static final String CMD_5E = "5E";
    public static final String CMD_60 = "60";
    public static final String CMD_61 = "61";
    public static final String CMD_62 = "62";
    public static final String CMD_63 = "63";
    public static final String CMD_64 = "64";
    public static final String CMD_65 = "65";
    public static final String CMD_66 = "66";
    public static final String CMD_67 = "67";
    public static final String CMD_68 = "68";
    public static final String CMD_69 = "69";
    public static final String CMD_6A = "6A";
    public static final String CMD_6B = "6B";
    public static final String CMD_6C = "6C";
    public static final String CMD_6D = "6D";
    public static final String CMD_6E = "6E";
    public static final String CMD_72 = "72";
    public static final String CMD_75 = "75";
    public static final String CMD_76 = "76";
    public static final String CMD_77 = "77";
    public static final String CMD_80 = "80";
    public static final String CMD_81 = "81";
    public static final String CMD_82 = "82";
    public static final String CMD_83 = "83";
    public static final String CMD_84 = "84";
    public static final String CMD_85 = "85";
    public static final String CMD_86 = "86";
    public static final String CMD_87 = "87";
    public static final String CMD_90 = "90";
    public static final String CMD_92 = "92";
    public static final String CMD_93 = "93";
    public static final String CMD_94 = "94";
    public static final String CMD_A0 = "A0";
    public static final String CMD_A3 = "A3";
    public static final String CMD_A4 = "A4";
    public static final short CMD_ID_8001 = -32767;
    public static final short CMD_ID_8002 = -32766;
    public static final short CMD_ID_8003 = -32765;
    public static final short CMD_ID_8004 = -32764;
    public static final short CMD_ID_8005 = -32763;
    public static final short CMD_ID_8006 = -32762;
    public static final short CMD_ID_8007 = -32761;
    public static final String CMD_READ_72 = "C072";
    public static final String CMD_READ_75 = "C075";
    public static final String CMD_READ_76 = "C076";
    public static final String CMD_READ_77 = "C077";
    public static final String CMD_READ_AUDIO_SPACE_58 = "C058";
    public static final String CMD_READ_AUTO_TYPE_56 = "C056";
    public static final String CMD_READ_BT_ADDRESS_06 = "C006";
    public static final String CMD_READ_BT_ANC_0C = "C00C";
    public static final String CMD_READ_BT_CHECK_0B = "C00B";
    public static final String CMD_READ_BT_GAME_SPACE_0F = "C00F";
    public static final String CMD_READ_BT_HEAR_HELP_16 = "C016";
    public static final String CMD_READ_BT_LOW_DELAY_0E = "C00E";
    public static final String CMD_READ_BT_NAME_54 = "C054";
    public static final String CMD_READ_BT_SPACE_0D = "C00D";
    public static final String CMD_READ_BT_STATUS_0A = "C00A";
    public static final String CMD_READ_CHECK_IN_EAR_55 = "C055";
    public static final String CMD_READ_CHIP_MODEL_03 = "C003";
    public static final String CMD_READ_DEVICE_ID_07 = "C007";
    public static final String CMD_READ_DIALOG_OP_50 = "C050";
    public static final String CMD_READ_DOUBLE_CLICK_LEFT_5C = "C05C";
    public static final String CMD_READ_DOUBLE_CLICK_RIGHT_5D = "C05D";
    public static final String CMD_READ_GAME_MODEL_57 = "C057";
    public static final String CMD_READ_GAME_SPACE_MODE_5E = "C05E";
    public static final String CMD_READ_LEFT_RIGHT_VERSION_STATUS_12 = "C012";
    public static final String CMD_READ_LONG_PRESS_LEFT_5A = "C05A";
    public static final String CMD_READ_LONG_PRESS_RIGHT_5B = "C05B";
    public static final String CMD_READ_NOISE_CONTROL_59 = "C059";
    public static final String CMD_READ_POWER_STATUS_09 = "C009";
    public static final String CMD_READ_PRODUCT_14 = "C014";
    public static final String CMD_READ_PRODUCT_DATE_15 = "C015";
    public static final String CMD_READ_PRODUCT_MODEL_04 = "C004";
    public static final String CMD_READ_PRODUCT_TYPE_08 = "C008";
    public static final String CMD_READ_SHAKE_HANDS_01 = "C0013D";
    public static final String CMD_READ_SN_CODE_51 = "C051";
    public static final String CMD_READ_SOFTWARE_VERSION_05 = "C005";
    public static final String CMD_READ_SUPPORT_OTA_13 = "C013";
    public static final String CMD_READ_VERIFY_02 = "C0023D";
    public static final String CMD_READ_VOICE_WAKE_52 = "C052";
    public static final String CMD_READ_WORK_STATUS_11 = "C011";
    public static final String CMD_STR_8001 = "0180";
    public static final String CMD_STR_8002 = "0280";
    public static final String CMD_STR_8003 = "0380";
    public static final String CMD_STR_8004 = "0480";
    public static final String CMD_STR_8005 = "0580";
    public static final int CMD_TYPE_BIU = 2;
    public static final int CMD_TYPE_HL = 1;
    public static final int CMD_TYPE_OTA = 3;
    public static final int CMD_TYPE_TEST = -1;
    public static final String CMD_WRITE_AUDIO_TYPE_66 = "C06601";
    public static final String CMD_WRITE_AUTO_CHECK_OFF = "C0650100";
    public static final String CMD_WRITE_AUTO_CHECK_ON = "C0650101";
    public static final String CMD_WRITE_BT_NAME = "C064";
    public static final String CMD_WRITE_CUSTOM_VOLUME_OFF = "C0850100";
    public static final String CMD_WRITE_CUSTOM_VOLUME_ON = "C0850101";
    public static final String CMD_WRITE_DIALOG_OP_60_OFF = "C0600102";
    public static final String CMD_WRITE_DIALOG_OP_60_ON = "C0600101";
    public static final String CMD_WRITE_DOUBLE_CLICK_LEFT = "C06C01";
    public static final String CMD_WRITE_DOUBLE_CLICK_RIGHT = "C06D01";
    public static final String CMD_WRITE_GAME_CHECK_OFF = "C0670100";
    public static final String CMD_WRITE_GAME_CHECK_ON = "C0670101";
    public static final String CMD_WRITE_GAME_SPACE_CHECK_OFF = "C06E0100";
    public static final String CMD_WRITE_GAME_SPACE_CHECK_ON = "C06E0101";
    public static final String CMD_WRITE_LONG_PRESS_LEFT = "C06A01";
    public static final String CMD_WRITE_LONG_PRESS_RIGHT = "C06B01";
    public static final String CMD_WRITE_LOW_HIGH_VOL_OFF = "C0870100";
    public static final String CMD_WRITE_LOW_HIGH_VOL_ON = "C0870101";
    public static final String CMD_WRITE_NOISE_CONTROL_69 = "C06901";
    public static final String CMD_WRITE_SPACE_AUDIO_68 = "C06801";
    public static final String CMD_WRITE_TALK_SENSITIVE_OFF = "C0860100";
    public static final String CMD_WRITE_TALK_SENSITIVE_ON = "C0860101";
    public static final String CMD_WRITE_VOICE_WAKE_OFF = "C0620100";
    public static final String CMD_WRITE_VOICE_WAKE_ON = "C0620101";
    public static final byte HEAD_COMMON = 11;
    public static final String HEAD_COMMON_0B = "0B";
    public static final byte HEAD_OTA = -86;
    public static final String HEAD_OTA_AA = "AA";
    public static final byte HEAD_VERIFY = 10;
    public static final String HEAD_VERIFY_0A = "0A";
    public static final int HEX_FFFF = 65535;
    public static final String OTA_CMD_04 = "55AA04";
    public static final String OTA_CMD_80 = "55AA80";
    public static final String OTA_CMD_81 = "55AA81";
    public static final String OTA_CMD_82 = "55AA82";
    public static final String OTA_CMD_83 = "55AA83";
    public static final String OTA_CMD_84 = "55AA84";
    public static final String OTA_L = "11";
    public static final String OTA_L_R = "33";
    public static final String OTA_R = "22";
    public static final String PRODUCT_TYPE_TWS_2 = "tws公版二代";
    public static final String PRODUCT_TYPE_TWS_3 = "tws公版三代";
    public static final String PRODUCT_TYPE_TWS_3_PRO = "tws公版pro";
    public static final String PRODUCT_TYPE_TWS_S = "tws私模";
    public static final String PRODUCT_TYPE_YP3 = "yp3";
    public static final String RANDOM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    public static final String SUPPORT_CORE_JU_PLUS = "TWS200|TWS200G|TWS206|tws200|tws200G|tws206";
    public static final String VERIFY_CODE = "534C";
    private static String mKey2;
    private static String mKeyData1;
    private static String mKeyData2;
    public static final byte[] CMD_ORDER_ARRAY = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
    public static int command_index = 0;
    public static byte DIVIDE_N_2 = 0;
    public static byte DIVIDE_N_JSON = 4;
    public static byte DIVIDE_Y_F_2 = 2;
    public static byte DIVIDE_Y_M_2 = 1;
    public static byte DIVIDE_Y_E_2 = 3;
    public static byte DIVIDE_Y_F_JSON = 6;
    public static byte DIVIDE_Y_M_JSON = 5;
    public static byte DIVIDE_Y_E_JSON = 7;
    public static boolean DEBUG_EQ = false;

    public static byte[] getHandshakeCmd() {
        StringBuffer stringBuffer = new StringBuffer();
        stringBuffer.append(CMD_READ_SHAKE_HANDS_01);
        stringBuffer.append(getRandomNumber(61));
        return BtUtils.hexStringToByteArray(stringBuffer.toString());
    }

    public static String[] getVerificationCommand() throws NumberFormatException {
        StringBuffer stringBuffer = new StringBuffer();
        stringBuffer.append(CMD_READ_VERIFY_02);
        stringBuffer.append(getRandomNumber(11));
        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(strArr[2]);
        int i = Integer.parseInt(strArr[1], 16);
        String[] strArr = {stringBuffer.toString(), getRandomNumber(2), getRandomNumber(32), getRandomNumber(16), BtUtils.bytesToHexString(bArrHexStringToByteArray)};
        strArr[2] = BtUtils.bytesToHexString(BtUtils.encryptData(i, bArrHexStringToByteArray, bArrHexStringToByteArray.length));
        return strArr;
    }

    private static String getRandomNumber(int i) {
        char[] charArray = RANDOM.toCharArray();
        Random random = new Random(System.currentTimeMillis());
        StringBuffer stringBuffer = new StringBuffer();
        for (int i2 = 0; i2 < i; i2++) {
            stringBuffer.append(charArray[random.nextInt(charArray.length)]);
        }
        return BtUtils.stringToHexString(stringBuffer.toString());
    }

    public static byte[] getReadFlashCmdArray(int i, int i2) {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(20);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -125);
        byteBufferAllocate.putInt(i);
        byteBufferAllocate.putInt(i2);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] constructCmd(byte b, short s, byte b2, int i, int i2, byte[] bArr) {
        int length = bArr == null ? 0 : bArr.length;
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(length + 16);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put(b);
        byte[] bArr2 = CMD_ORDER_ARRAY;
        byteBufferAllocate.put(bArr2[command_index % bArr2.length]);
        byteBufferAllocate.putShort((short) (s & ShortCompanionObject.MAX_VALUE));
        byteBufferAllocate.put(b2);
        byteBufferAllocate.put((byte) 0);
        byteBufferAllocate.putShort((short) length);
        byteBufferAllocate.putInt(i);
        byteBufferAllocate.putInt(i2);
        if (bArr != null) {
            byteBufferAllocate.put(bArr);
        }
        byteBufferAllocate.flip();
        command_index++;
        return byteBufferAllocate.array();
    }

    public static byte[] getBiuShakeHandsCmd() {
        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(getRandomNumber(61));
        return constructCmd((byte) 10, CMD_ID_8001, DIVIDE_N_2, 0, BtUtils.crc8Maxim(bArrHexStringToByteArray, bArrHexStringToByteArray.length), bArrHexStringToByteArray);
    }

    public static byte[] getBiuVerifyCmd() throws NumberFormatException {
        byte[] verifyPayload = getVerifyPayload();
        return constructCmd((byte) 10, CMD_ID_8002, DIVIDE_N_2, 0, BtUtils.crc8Maxim(verifyPayload, verifyPayload.length), verifyPayload);
    }

    public static byte[] getVerifyPayload() throws NumberFormatException {
        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(strArr[2]);
        int i = Integer.parseInt(strArr[1], 16);
        String[] strArr = {getRandomNumber(14), getRandomNumber(2), getRandomNumber(32), getRandomNumber(16), BtUtils.bytesToHexString(bArrHexStringToByteArray)};
        strArr[2] = BtUtils.bytesToHexString(BtUtils.encryptData(i, bArrHexStringToByteArray, bArrHexStringToByteArray.length));
        mKeyData1 = strArr[3];
        mKeyData2 = strArr[4];
        mKey2 = BtUtils.getTheAccumulatedValueAnd(strArr[2]);
        return BtUtils.hexStringToByteArray(strArr[0] + strArr[1] + strArr[2] + strArr[3]);
    }

    public static String getTheAccumulatedValueAnd(String str) {
        if (TextUtils.isEmpty(str)) {
            return "";
        }
        int length = str.length();
        int i = 0;
        int i2 = 0;
        while (i < length) {
            int i3 = i + 2;
            i2 += Integer.parseInt(str.substring(i, i3), 16);
            i = i3;
        }
        return Integer.toHexString(i2);
    }

    public static BiuMsgBean getPayLoadJson(byte[] bArr) {
        BiuMsgBean biuMsgBean = new BiuMsgBean();
        ByteBuffer byteBufferWrap = ByteBuffer.wrap(bArr);
        biuMsgBean.head = byteBufferWrap.get();
        biuMsgBean.cmdOrder = byteBufferWrap.get();
        byte[] bArr2 = new byte[2];
        System.arraycopy(bArr, 2, bArr2, 0, 2);
        biuMsgBean.cmdStr = BtUtils.bytesToHexString(bArr2);
        byte b = byteBufferWrap.get(4);
        biuMsgBean.divideType = b;
        LogUtil.logBlueTooth("divideType:" + ((int) b));
        byte[] bArr3 = new byte[2];
        System.arraycopy(bArr, 5, bArr3, 0, 2);
        String strBytesToHexString = BtUtils.bytesToHexString(bArr3);
        LogUtil.logBlueTooth("lenHex:" + strBytesToHexString);
        int iHexToInt = BtUtils.hexToInt(strBytesToHexString);
        LogUtil.logBlueTooth("length:" + iHexToInt);
        biuMsgBean.payloadLen = iHexToInt;
        byte[] bArr4 = new byte[4];
        System.arraycopy(bArr, 8, bArr4, 0, 4);
        biuMsgBean.offset = ByteUtil.bytesToInt(bArr4, ByteOrder.LITTLE_ENDIAN);
        byte[] bArr5 = new byte[4];
        System.arraycopy(bArr, 12, bArr5, 0, 4);
        biuMsgBean.crc = ByteUtil.bytesToInt(bArr5, ByteOrder.LITTLE_ENDIAN);
        if (iHexToInt > 0) {
            byte[] bArr6 = new byte[iHexToInt];
            System.arraycopy(bArr, 16, bArr6, 0, iHexToInt);
            biuMsgBean.payload = bArr6;
            if (b == DIVIDE_N_JSON) {
                String str = new String(bArr6, StandardCharsets.UTF_8);
                biuMsgBean.payloadJson = str;
                LogUtil.logBlueTooth("payloadJson:" + str);
            }
        }
        LogUtil.logBlueTooth("返回消息封装:" + biuMsgBean.toString());
        return biuMsgBean;
    }

    public static boolean verificationCmd(String str) {
        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(str.substring(32, 96));
        String strBytesToHexString = BtUtils.bytesToHexString(BtUtils.encryptData(Integer.parseInt(mKey2, 16), bArrHexStringToByteArray, bArrHexStringToByteArray.length));
        String strSubstring = strBytesToHexString.substring(0, 32);
        String strSubstring2 = strBytesToHexString.substring(32);
        byte[] bArrHexStringToByteArray2 = BtUtils.hexStringToByteArray(strSubstring);
        byte[] bArrHexStringToByteArray3 = BtUtils.hexStringToByteArray(strSubstring2);
        byte[] bArrHexStringToByteArray4 = BtUtils.hexStringToByteArray(mKeyData1);
        byte[] bArr = new byte[bArrHexStringToByteArray2.length + bArrHexStringToByteArray3.length];
        for (int i = 0; i < bArrHexStringToByteArray2.length; i++) {
            bArr[i] = (byte) (bArrHexStringToByteArray2[i] ^ bArrHexStringToByteArray4[i]);
        }
        for (int i2 = 0; i2 < bArrHexStringToByteArray3.length; i2++) {
            bArr[bArrHexStringToByteArray3.length + i2] = (byte) (bArrHexStringToByteArray3[i2] ^ bArrHexStringToByteArray4[i2]);
        }
        return BtUtils.bytesToHexString(bArr).equalsIgnoreCase(mKeyData2);
    }

    public static byte[] isSupportEqCmd() {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(2);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put(Ascii.ETB);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] readDefEqListCmd() {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(2);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -112);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] readCustomEqParamsCmd() {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(2);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -110);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] readCustomEqDataLenCmd() {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(2);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -109);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] readCustomEqDataCmd(byte b, byte b2) {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(4);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -108);
        byteBufferAllocate.put(b);
        byteBufferAllocate.put(b2);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] writeDefEqIndexCmd(byte b) {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(4);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -96);
        byteBufferAllocate.put((byte) 1);
        byteBufferAllocate.put(b);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] writeCustomEqDataCmd(byte[] bArr) {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(bArr.length + 3);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -93);
        byteBufferAllocate.put((byte) bArr.length);
        byteBufferAllocate.put(bArr);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] saveCustomEqDataCmd(int i, byte[] bArr) {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(bArr.length + 4);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) -64);
        byteBufferAllocate.put((byte) -92);
        byteBufferAllocate.put((byte) (bArr.length + 1));
        byteBufferAllocate.put((byte) i);
        byteBufferAllocate.put(bArr);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }

    public static byte[] getCustomEqItemCmd(int i, float f) {
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(8);
        byteBufferAllocate.order(ByteOrder.LITTLE_ENDIAN);
        byteBufferAllocate.put((byte) 0);
        byteBufferAllocate.put((byte) i);
        byteBufferAllocate.put((byte) 0);
        byteBufferAllocate.put((byte) 0);
        byteBufferAllocate.putFloat(f);
        byteBufferAllocate.flip();
        return byteBufferAllocate.array();
    }
}
