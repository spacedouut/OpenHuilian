package com.shenju.ota.utils;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.content.Context;
import android.content.IntentFilter;
import android.text.TextUtils;
import android.util.Log;
import cn.hutool.core.text.CharSequenceUtil;
import cn.hutool.core.util.ArrayUtil;
import cn.hutool.core.util.ByteUtil;
import com.alibaba.idst.nui.Constants;
import com.mobile.mobilehardware.base.BaseData;
import com.shenju.ota.entity.DeviceBean;
import com.shenju.ota.entity.UpInfoData;
import com.shenju.uparser.UparserJni;
import com.sjbt.lib_common.utils.Encode;
import java.nio.ByteOrder;
import org.bouncycastle.asn1.cmc.BodyPartID;

/* loaded from: classes2.dex */
public class BtUtils {
    private static final String TAG_BLUETOOTH = ">>>>>>>>bluetooth";
    private static boolean isOpenLog = true;

    public static native char crc8Maxim(byte[] bArr, int i);

    public static native byte[] encryptData(int i, byte[] bArr, int i2);

    public static native int getCrc(int i, byte[] bArr, int i2);

    static {
        System.loadLibrary("uparser-lib");
    }

    public static String stringToHexString(String str) {
        String str2 = "";
        for (int i = 0; i < str.length(); i++) {
            str2 = str2 + Integer.toHexString(str.charAt(i));
        }
        return str2;
    }

    public static short byte2short(byte[] bArr) {
        short s = 0;
        for (int i = 0; i < 2; i++) {
            s = (short) (((short) (s << 8)) | (bArr[i] & 255));
        }
        return s;
    }

    public static String intToHex(int i) {
        String hexString = Integer.toHexString(i);
        if (hexString.length() != 1 || !hexString.matches("[0-9A-Za-z]+")) {
            return hexString;
        }
        return Constants.ModeFullMix + hexString;
    }

    public static int hexToInt(String str) {
        int length = str.length();
        int i = 0;
        for (int i2 = 0; i2 < length; i2++) {
            int iCodePointAt = str.codePointAt(i2);
            i = (i << 4) | (iCodePointAt > 57 ? iCodePointAt - 55 : iCodePointAt - 48);
        }
        return i;
    }

    public static int hexToIntLittleEndian(String str) {
        int length = str.length();
        if (length % 2 != 0) {
            throw new IllegalArgumentException("Hex string length must be even");
        }
        int i = 0;
        for (int i2 = 0; i2 < length; i2 += 2) {
            int iCodePointAt = str.codePointAt(i2);
            int i3 = iCodePointAt > 57 ? iCodePointAt - 55 : iCodePointAt - 48;
            int iCodePointAt2 = str.codePointAt(i2 + 1);
            i |= ((i3 << 4) | (iCodePointAt2 > 57 ? iCodePointAt2 - 55 : iCodePointAt2 - 48)) << (i2 * 4);
        }
        return i;
    }

    public static String hexStringToString(String str) {
        if (str == null || str.equals("")) {
            return null;
        }
        String strReplace = str.replace(CharSequenceUtil.SPACE, "");
        int length = strReplace.length() / 2;
        byte[] bArr = new byte[length];
        for (int i = 0; i < length; i++) {
            int i2 = i * 2;
            try {
                bArr[i] = (byte) (Integer.parseInt(strReplace.substring(i2, i2 + 2), 16) & 255);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        try {
            return new String(bArr, Encode.UTF_8);
        } catch (Exception e2) {
            e2.printStackTrace();
            return strReplace;
        }
    }

    public static byte[] hexStringToByteArray(String str) {
        int length = str.length();
        byte[] bArr = new byte[length / 2];
        for (int i = 0; i < length; i += 2) {
            bArr[i / 2] = (byte) ((Character.digit(str.charAt(i), 16) << 4) + Character.digit(str.charAt(i + 1), 16));
        }
        return bArr;
    }

    public static String bytesToHexString(byte[] bArr) {
        StringBuffer stringBuffer = new StringBuffer(bArr.length);
        for (byte b : bArr) {
            String hexString = Integer.toHexString(b & 255);
            if (hexString.length() < 2) {
                stringBuffer.append(0);
            }
            stringBuffer.append(hexString);
        }
        return stringBuffer.toString().toUpperCase();
    }

    public static String getSplitReverseHexStringCmd(String str, int i) {
        StringBuilder sb = new StringBuilder();
        for (int i2 = 0; i2 < (i * 2) - str.length(); i2++) {
            sb.append(Constants.ModeFullMix);
        }
        sb.append(str);
        int length = sb.length() / 2;
        String[] strArr = new String[length];
        for (int i3 = 0; i3 < length; i3++) {
            int i4 = i3 * 2;
            strArr[i3] = sb.substring(i4, i4 + 2);
        }
        String[] strArr2 = (String[]) ArrayUtil.reverse(strArr);
        StringBuilder sb2 = new StringBuilder();
        for (String str2 : strArr2) {
            sb2.append(str2);
        }
        return sb2.toString();
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

    public static boolean verificationCmd(String str, String str2, String str3, String str4) {
        byte[] bArrHexStringToByteArray = hexStringToByteArray(str.substring(32, 96));
        String strBytesToHexString = bytesToHexString(encryptData(Integer.parseInt(str2, 16), bArrHexStringToByteArray, bArrHexStringToByteArray.length));
        String strSubstring = strBytesToHexString.substring(0, 32);
        String strSubstring2 = strBytesToHexString.substring(32);
        byte[] bArrHexStringToByteArray2 = hexStringToByteArray(strSubstring);
        byte[] bArrHexStringToByteArray3 = hexStringToByteArray(strSubstring2);
        byte[] bArrHexStringToByteArray4 = hexStringToByteArray(str3);
        byte[] bArr = new byte[bArrHexStringToByteArray2.length + bArrHexStringToByteArray3.length];
        for (int i = 0; i < bArrHexStringToByteArray2.length; i++) {
            bArr[i] = (byte) (bArrHexStringToByteArray2[i] ^ bArrHexStringToByteArray4[i]);
        }
        for (int i2 = 0; i2 < bArrHexStringToByteArray3.length; i2++) {
            bArr[bArrHexStringToByteArray3.length + i2] = (byte) (bArrHexStringToByteArray3[i2] ^ bArrHexStringToByteArray4[i2]);
        }
        return bytesToHexString(bArr).equalsIgnoreCase(str4);
    }

    public static UpInfoData getUploadContent(byte[] bArr) {
        UpInfoData upInfoData = new UpInfoData();
        int length = bArr.length - 256;
        byte[] bArr2 = new byte[length];
        System.arraycopy(bArr, 256, bArr2, 0, length);
        byte[] bArr3 = new byte[96];
        System.arraycopy(bArr2, 0, bArr3, 0, 96);
        byte[] bArr4 = new byte[4];
        System.arraycopy(bArr3, 32, bArr4, 0, 4);
        int iBytesToInt = ByteUtil.bytesToInt(bArr4, ByteOrder.LITTLE_ENDIAN);
        upInfoData.indexPosition = iBytesToInt;
        logBlueTooth("索引区的位置：" + intToHex(upInfoData.indexPosition));
        byte[] bArr5 = new byte[4];
        System.arraycopy(bArr2, iBytesToInt, bArr5, 0, 4);
        int iBytesToInt2 = ByteUtil.bytesToInt(bArr5);
        upInfoData.partitionNum = iBytesToInt2;
        logBlueTooth("分区个数:" + iBytesToInt2);
        StringBuilder sb = new StringBuilder();
        sb.append("索引区长度:");
        int i = (iBytesToInt2 + 1) * 16;
        sb.append(i);
        logBlueTooth(sb.toString());
        byte[] bArr6 = new byte[i];
        System.arraycopy(bArr2, iBytesToInt, bArr6, 0, i);
        byte[] bArr7 = new byte[4];
        System.arraycopy(bArr6, 4, bArr7, 0, 4);
        for (int i2 = 0; i2 < 4; i2++) {
            bArr7[i2] = (byte) (bArr7[i2] & 255);
        }
        upInfoData.version = String.valueOf(fourBytes2Long(bArr7, ByteOrder.LITTLE_ENDIAN));
        logBlueTooth("UP版本号：" + upInfoData.version);
        upInfoData.indexByteArray = bArr6;
        for (int i3 = 1; i3 <= iBytesToInt2; i3++) {
            byte[] bArr8 = new byte[4];
            byte[] bArr9 = new byte[4];
            byte[] bArr10 = new byte[4];
            byte[] bArr11 = new byte[4];
            int i4 = i3 * 16;
            System.arraycopy(bArr6, i4, bArr8, 0, 4);
            System.arraycopy(bArr6, i4 + 4, bArr9, 0, 4);
            System.arraycopy(bArr6, i4 + 8, bArr10, 0, 4);
            System.arraycopy(bArr6, i4 + 12, bArr11, 0, 4);
            String strBytesToHexString = bytesToHexString(bArr8);
            int iBytesToInt3 = ByteUtil.bytesToInt(bArr9);
            String strBytesToHexString2 = bytesToHexString(bArr11);
            int iBytesToInt4 = ByteUtil.bytesToInt(bArr10);
            String strHexStringToString = hexStringToString(strBytesToHexString);
            logBlueTooth("本地分区名称:" + strHexStringToString);
            logBlueTooth("本地分区addr:" + intToHex(iBytesToInt3));
            logBlueTooth("本地分区length:" + iBytesToInt4);
            logBlueTooth("本地分区crc:" + strBytesToHexString2);
            if (strHexStringToString.equals(UparserJni.TAG_FIRM)) {
                upInfoData.firmwarePosition = iBytesToInt3;
                upInfoData.firmwareLength = iBytesToInt4;
            }
            if (strHexStringToString.equals(UparserJni.TAG_OTAP)) {
                int i5 = iBytesToInt3 - iBytesToInt;
                byte[] bArr12 = new byte[i5];
                System.arraycopy(bArr2, iBytesToInt, bArr12, 0, i5);
                upInfoData.otaPosition = iBytesToInt3;
                upInfoData.upPartByteArrayWithIndex = bArr12;
                int i6 = iBytesToInt3 - upInfoData.firmwarePosition;
                byte[] bArr13 = new byte[i6];
                System.arraycopy(bArr2, upInfoData.firmwarePosition, bArr13, 0, i6);
                upInfoData.upPartByteArrayWithOutIndex = bArr13;
                return upInfoData;
            }
        }
        return upInfoData;
    }

    public static DeviceBean createBluetoothItem(BluetoothDevice bluetoothDevice) {
        DeviceBean deviceBean = new DeviceBean();
        deviceBean.setBluetoothDevice(bluetoothDevice);
        return deviceBean;
    }

    public static boolean isBlueEnable(Context context) {
        BluetoothAdapter adapter = ((BluetoothManager) context.getSystemService("bluetooth")).getAdapter();
        return adapter != null && adapter.isEnabled();
    }

    public static int getPhoneBattery(Context context) {
        return context.getApplicationContext().registerReceiver(null, new IntentFilter("android.intent.action.BATTERY_CHANGED")).getIntExtra(BaseData.Signal.LEVEL, 0);
    }

    public static long fourBytes2Long(byte[] bArr, ByteOrder byteOrder) {
        int i;
        byte b;
        if (ByteOrder.LITTLE_ENDIAN == byteOrder) {
            i = (bArr[0] & 255) | ((bArr[1] & 255) << 8) | ((bArr[2] & 255) << 16);
            b = bArr[3];
        } else {
            i = (bArr[3] & 255) | ((bArr[2] & 255) << 8) | ((bArr[1] & 255) << 16);
            b = bArr[0];
        }
        return (((b & 255) << 24) | i) & BodyPartID.bodyIdMax;
    }

    public static void logBlueTooth(String str) {
        if (isOpenLog) {
            Log.e(">>>>>>>>bluetooth", str);
        }
    }

    public static boolean isSameDevice(String str, DeviceBean deviceBean) {
        if (TextUtils.isEmpty(str) || deviceBean == null || deviceBean.getBluetoothDevice() == null || TextUtils.isEmpty(deviceBean.getBluetoothDevice().getAddress())) {
            return false;
        }
        return str.equalsIgnoreCase(deviceBean.getBluetoothDevice().getAddress());
    }
}
