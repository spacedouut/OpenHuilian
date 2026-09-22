package com.shenju.ota;

import com.shenju.ota.entity.OtaInfoData;
import com.shenju.ota.entity.UpInfoData;
import com.shenju.ota.utils.BtUtils;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.List;

/* loaded from: classes2.dex */
public class OtaCmdConfig {
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
    public static final String CMD_10 = "10";
    public static final String CMD_11 = "11";
    public static final String CMD_12 = "12";
    public static final String CMD_13 = "13";
    public static final String CMD_4 = "04";
    public static final String CMD_80 = "80";
    public static final String CMD_81 = "81";
    public static final String CMD_82 = "82";
    public static final String CMD_83 = "83";
    public static final String CMD_84 = "84";
    public static final String CMD_READ_LEFT_RIGHT_VERSION_STATUS = "C012";
    public static final String CMD_READ_POWER_STATUS_09 = "C009";
    public static final String CMD_READ_PRODUCT_MODEL_04 = "C004";
    public static final String CMD_READ_SOFTWARE_VERSION_05 = "C005";
    public static final String CMD_READ_SUPPORT_OTA = "C013";
    public static final String CMD_READ_WORK_STATUS = "C011";
    public static final int CMD_TYPE_BIU = 2;
    public static final int CMD_TYPE_HL = 1;
    public static final int CMD_TYPE_OTA = 3;
    public static final int CMD_TYPE_TEST = -1;
    public static final String HEAD_OTA_LOW = "55aa";
    public static final String HEAD_OTA_UPPER = "55AA";
    public static final String OTA_CMD_04 = "55AA04";
    public static final String OTA_CMD_80 = "55AA80";
    public static final String OTA_CMD_81 = "55AA81";
    public static final String OTA_CMD_82 = "55AA82";
    public static final String OTA_CMD_83 = "55AA83";
    public static final String OTA_CMD_84 = "55AA84";
    public static final String OTA_L = "11";
    public static final String OTA_L_R = "33";
    public static final String OTA_R = "22";
    public static final String VERIFY_CODE = "534C";

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

    public static List<OtaInfoData> packCmd83Data(UpInfoData upInfoData) {
        String str;
        int i;
        String str2;
        ArrayList arrayList = new ArrayList();
        byte[] bArr = upInfoData.upPartByteArrayWithOutIndex;
        byte[] bArr2 = upInfoData.indexByteArray;
        int i2 = 512;
        int length = bArr.length % 512;
        int length2 = bArr.length / 512;
        if (length != 0) {
            length2++;
        }
        int i3 = length2;
        int i4 = 520;
        String str3 = " offset:";
        String str4 = "索引部分 length：";
        int i5 = 2;
        int i6 = 0;
        int i7 = 4;
        if (length == 0) {
            int i8 = 0;
            while (i8 < i3) {
                byte[] bArr3 = new byte[i2];
                int i9 = i8 * 512;
                System.arraycopy(bArr, i9, bArr3, i6, i2);
                addOtaData(arrayList, i8, "55AA83", BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(i4), i5), BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.firmwarePosition + i9), i7), BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(i2), i7), BtUtils.bytesToHexString(bArr3));
                i8++;
                str4 = str4;
                str3 = str3;
                i7 = 4;
                i6 = 0;
                i5 = 2;
                i2 = 512;
                i4 = 520;
            }
            String str5 = str4;
            int length3 = bArr2.length;
            String strBytesToHexString = BtUtils.bytesToHexString(bArr2);
            String splitReverseHexStringCmd = BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(length3 + 8), 2);
            String splitReverseHexStringCmd2 = BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.indexPosition), 4);
            String splitReverseHexStringCmd3 = BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(length3), 4);
            BtUtils.logBlueTooth(str5 + splitReverseHexStringCmd + str3 + splitReverseHexStringCmd2 + " dataLength:" + splitReverseHexStringCmd3);
            addOtaData(arrayList, i3 + 1, "55AA83", splitReverseHexStringCmd, splitReverseHexStringCmd2, splitReverseHexStringCmd3, strBytesToHexString);
        } else {
            String str6 = " offset:";
            int i10 = 2;
            int i11 = 4;
            String str7 = "索引部分 length：";
            int i12 = 0;
            while (i12 < i3) {
                if (i12 < i3 - 1) {
                    byte[] bArr4 = new byte[512];
                    int i13 = i12 * 512;
                    System.arraycopy(bArr, i13, bArr4, 0, 512);
                    String str8 = str6;
                    str = str8;
                    i = i12;
                    str2 = str7;
                    addOtaData(arrayList, i12, "55AA83", BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(520), i10), BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.firmwarePosition + i13), i11), BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(512), i11), BtUtils.bytesToHexString(bArr4));
                } else {
                    str = str6;
                    i = i12;
                    str2 = str7;
                    byte[] bArr5 = new byte[length];
                    int i14 = i * 512;
                    System.arraycopy(bArr, i14, bArr5, 0, length);
                    addOtaData(arrayList, i, "55AA83", BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(length + 8), 2), BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.firmwarePosition + i14), 4), BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(length), 4), BtUtils.bytesToHexString(bArr5));
                }
                i12 = i + 1;
                str6 = str;
                str7 = str2;
                i10 = 2;
                i11 = 4;
            }
            String strBytesToHexString2 = BtUtils.bytesToHexString(bArr2);
            String splitReverseHexStringCmd4 = BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(bArr2.length + 8), 2);
            String splitReverseHexStringCmd5 = BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.indexPosition), 4);
            String splitReverseHexStringCmd6 = BtUtils.getSplitReverseHexStringCmd(BtUtils.intToHex(bArr2.length), 4);
            BtUtils.logBlueTooth(str7 + splitReverseHexStringCmd4 + str6 + splitReverseHexStringCmd5 + " dataLength:" + splitReverseHexStringCmd6);
            addOtaData(arrayList, i3 + 1, "55AA83", splitReverseHexStringCmd4, splitReverseHexStringCmd5, splitReverseHexStringCmd6, strBytesToHexString2);
        }
        return arrayList;
    }

    private static void addOtaData(List<OtaInfoData> list, int i, String str, String str2, String str3, String str4, String str5) {
        StringBuilder sb = new StringBuilder();
        sb.append(str);
        sb.append(str2);
        sb.append(str3);
        sb.append(str4);
        sb.append(str5);
        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(sb.toString());
        sb.append(BtUtils.intToHex(BtUtils.crc8Maxim(bArrHexStringToByteArray, bArrHexStringToByteArray.length)));
        OtaInfoData otaInfoData = new OtaInfoData();
        otaInfoData.cmd = sb.toString();
        otaInfoData.id = i;
        otaInfoData.offset_Length = str3 + str4;
        list.add(otaInfoData);
    }
}
