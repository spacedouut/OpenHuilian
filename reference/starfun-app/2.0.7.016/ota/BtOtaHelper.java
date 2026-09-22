package com.shenju.ota;

import android.bluetooth.BluetoothDevice;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.widget.Toast;
import cn.hutool.core.io.FileUtil;
import cn.hutool.core.io.IORuntimeException;
import cn.hutool.core.text.CharSequenceUtil;
import com.shenju.ota.entity.DeviceBean;
import com.shenju.ota.entity.EqToneBean;
import com.shenju.ota.entity.OtaInfoData;
import com.shenju.ota.entity.UpInfoData;
import com.shenju.ota.utils.BtUtils;
import com.shenju.ota.utils.UParseUtil;
import com.tencent.mmkv.MMKV;
import io.reactivex.rxjava3.android.schedulers.AndroidSchedulers;
import io.reactivex.rxjava3.core.Observable;
import io.reactivex.rxjava3.core.ObservableEmitter;
import io.reactivex.rxjava3.core.ObservableOnSubscribe;
import io.reactivex.rxjava3.core.Observer;
import io.reactivex.rxjava3.disposables.Disposable;
import io.reactivex.rxjava3.schedulers.Schedulers;
import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;

/* loaded from: classes2.dex */
public class BtOtaHelper {
    private static final int GET_FLASH_LENGTH = 100;
    private static final int INDEX_LENGTH = 200;
    private static final int INDEX_START_ADDRESS = 12288;
    private static BtOtaHelper otaHelper = new BtOtaHelper();
    private byte[] cmd82Array;
    private DeviceBean deviceBean;
    private Disposable disposable;
    private EqToneBean eqToneBean;
    private Context mContext;
    protected Handler mHandler;
    private UpInfoData mUpInfoData;
    private String originUpPath;
    private OtaConnectCallBack otaConnectCallBack;
    private List<OtaInfoData> otaInfoDataList;
    private BtOtaListener otaListener;
    private int ota_step;
    private StringBuffer sbEqData;
    private StringBuffer sbToneData;
    private boolean stopCheckBattery;
    private Timer timer;
    private TimerTask timerTask;
    private String TAG = "BtOtaHelper";
    private int ota_process = 0;
    private String left_right = "11";
    private int otaTimeOutErrCount = 0;
    private int index = 1;
    private int eq_tone_address = INDEX_START_ADDRESS;
    private int eq_tone_length = 200;

    public void onSendMsg(byte[] bArr) {
    }

    private BtOtaHelper() {
    }

    public static BtOtaHelper getInstance() {
        return otaHelper;
    }

    public boolean isInit() {
        return (this.mContext == null || this.deviceBean == null) ? false : true;
    }

    public void init(Context context, BluetoothDevice bluetoothDevice, BtOtaListener btOtaListener) {
        if (isInit()) {
            return;
        }
        this.mContext = context;
        this.mHandler = new Handler(Looper.getMainLooper());
        DeviceBean deviceBeanCreateBluetoothItem = BtUtils.createBluetoothItem(bluetoothDevice);
        this.deviceBean = deviceBeanCreateBluetoothItem;
        deviceBeanCreateBluetoothItem.setConnected(true);
        this.otaListener = btOtaListener;
        this.otaInfoDataList = new ArrayList();
        this.eqToneBean = new EqToneBean();
        this.sbEqData = new StringBuffer();
        this.sbToneData = new StringBuffer();
        this.timer = new Timer();
        this.timerTask = new TimerTask() { // from class: com.shenju.ota.BtOtaHelper.1
            @Override // java.util.TimerTask, java.lang.Runnable
            public void run() {
                if (BtOtaHelper.this.deviceBean == null || !BtOtaHelper.this.deviceBean.isConnected || BtOtaHelper.this.stopCheckBattery) {
                    return;
                }
                BtOtaHelper.this.sendNormalMsg("C009");
            }
        };
        sendNormalMsg("C004");
        this.timer.scheduleAtFixedRate(this.timerTask, 300L, 2000L);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendNormalMsg(String str) {
        this.otaListener.onSendMsg(BtUtils.hexStringToByteArray(str), 1);
    }

    private void sendOtaMsg(String str) {
        this.otaListener.onSendMsg(getOtaCmdWithCrc(str + this.left_right + "00"), 3);
    }

    private byte[] getOtaCmdWithCrc(String str) {
        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(str);
        return BtUtils.hexStringToByteArray(str + BtUtils.intToHex(BtUtils.crc8Maxim(bArrHexStringToByteArray, bArrHexStringToByteArray.length)));
    }

    public void prepareOta() {
        checkOtaStatus(true);
    }

    public void startOta() {
        if (checkOtaStatus(false)) {
            if (TextUtils.isEmpty(this.originUpPath)) {
                Toast.makeText(this.mContext, ".up file path is empty!", 0).show();
                return;
            }
            this.ota_step = 1;
            this.stopCheckBattery = true;
            this.ota_process = 0;
            sendOtaMsg("55AA80");
        }
    }

    private boolean checkOtaStatus(boolean z) {
        if (this.otaListener == null) {
            throw new RuntimeException("NOT INIT EXCEPTION");
        }
        if (isVersionDateOk()) {
            if (BtUtils.getPhoneBattery(this.mContext) > 30) {
                if (BtUtils.isBlueEnable(this.mContext)) {
                    if (this.deviceBean.isConnected) {
                        if (this.deviceBean.isLeftConnect && this.deviceBean.isRightConnect) {
                            if (this.deviceBean.getLeftBattery() >= 50 && this.deviceBean.getRightBattery() >= 50) {
                                if (!this.deviceBean.isCharging) {
                                    if (!isDeviceSupportOta()) {
                                        this.otaListener.onConditionFail(8);
                                        return false;
                                    }
                                    if (!z) {
                                        return true;
                                    }
                                    this.otaListener.onAllConditionsOk();
                                    return true;
                                }
                                this.otaListener.onConditionFail(7);
                                return false;
                            }
                            this.otaListener.onConditionFail(6);
                            return false;
                        }
                        this.otaListener.onConditionFail(4);
                        return false;
                    }
                    this.otaListener.onConditionFail(3);
                    return false;
                }
                this.otaListener.onConditionFail(2);
                return false;
            }
            this.otaListener.onConditionFail(5);
            return false;
        }
        this.otaListener.onConditionFail(9);
        return false;
    }

    private boolean isVersionDateOk() throws NumberFormatException {
        DeviceBean deviceBean = this.deviceBean;
        if (deviceBean == null || TextUtils.isEmpty(deviceBean.version) || TextUtils.isEmpty(this.deviceBean.modelType)) {
            return false;
        }
        String str = this.deviceBean.version;
        if (TextUtils.isEmpty(str) || str.length() < 7) {
            return false;
        }
        long j = Long.parseLong(str.substring(0, 6));
        return this.deviceBean.modelType.replaceAll(CharSequenceUtil.SPACE, "").toLowerCase().equals("a10") ? j > 220411 : j > 220408;
    }

    public void onMsgTimeOut(byte[] bArr) {
        boolean z;
        if (this.otaListener == null) {
            throw new RuntimeException("NOT INIT EXCEPTION");
        }
        if (!BtUtils.isBlueEnable(this.mContext)) {
            this.ota_process = 0;
            this.otaListener.onConditionFail(2);
            return;
        }
        String strBytesToHexString = BtUtils.bytesToHexString(bArr);
        String strSubstring = strBytesToHexString.substring(2, 4);
        if (strBytesToHexString.startsWith(OtaCmdConfig.HEAD_OTA_UPPER) || strBytesToHexString.startsWith(OtaCmdConfig.HEAD_OTA_LOW)) {
            strSubstring = strBytesToHexString.substring(4, 6);
            z = true;
        } else {
            z = false;
        }
        BtUtils.logBlueTooth("消息发送超时：" + strSubstring);
        strSubstring.hashCode();
        switch (strSubstring) {
            case "13":
                this.otaListener.onConditionFail(8);
                BtUtils.logBlueTooth("onConditionFail 配置同步 13超时出错超过限制");
                return;
            case "80":
                int i = this.otaTimeOutErrCount + 1;
                this.otaTimeOutErrCount = i;
                if (i > 6) {
                    this.otaTimeOutErrCount = 0;
                    this.otaListener.onUpGradeFail(12);
                    BtUtils.logBlueTooth("onUpGradeFail 80超时出错超过限制");
                    return;
                }
                sendOtaMsg("55AA80");
                return;
            case "81":
                int i2 = this.otaTimeOutErrCount + 1;
                this.otaTimeOutErrCount = i2;
                if (i2 > 6) {
                    this.otaTimeOutErrCount = 0;
                    this.otaListener.onUpGradeFail(12);
                    BtUtils.logBlueTooth("onUpGradeFail 81超时出错超过限制");
                    return;
                }
                sendOtaMsg("55AA81");
                return;
            case "83":
                if (z) {
                    if (this.otaTimeOutErrCount > 6) {
                        this.otaTimeOutErrCount = 0;
                        this.otaListener.onUpGradeFail(12);
                        BtUtils.logBlueTooth("onUpGradeFail 83超时出错超过限制");
                        return;
                    } else {
                        if (this.ota_process < this.otaInfoDataList.size()) {
                            int i3 = this.ota_step;
                            if (i3 == 1 || i3 == 2) {
                                BtUtils.logBlueTooth("83命令超时，重发次数：" + this.otaTimeOutErrCount);
                                this.otaTimeOutErrCount = this.otaTimeOutErrCount + 1;
                                sendOtaMsg(this.otaInfoDataList.get(this.ota_process).cmd);
                                return;
                            }
                            return;
                        }
                        return;
                    }
                }
                int i4 = this.otaTimeOutErrCount;
                if (i4 > 6) {
                    this.otaTimeOutErrCount = 0;
                    this.otaListener.onUpGradeFail(12);
                    BtUtils.logBlueTooth("onUpGradeFail 配置同步 83超时出错超过限制");
                    return;
                } else {
                    this.otaTimeOutErrCount = i4 + 1;
                    BtUtils.logBlueTooth("EQ同步83命令超时，重发次数：" + this.otaTimeOutErrCount);
                    sendDeviceEqToneCmd(this.eq_tone_address, this.eq_tone_length);
                    return;
                }
            default:
                return;
        }
    }

    public void onGetMsg(byte[] bArr) {
        if (this.otaListener == null) {
            throw new RuntimeException("NOT INIT EXCEPTION");
        }
        final String strBytesToHexString = BtUtils.bytesToHexString(bArr);
        this.mHandler.post(new Runnable() { // from class: com.shenju.ota.BtOtaHelper.2
            @Override // java.lang.Runnable
            public void run() {
                if (strBytesToHexString.startsWith(OtaCmdConfig.HEAD_OTA_UPPER) || strBytesToHexString.startsWith(OtaCmdConfig.HEAD_OTA_LOW)) {
                    BtOtaHelper.this.otaBuz(strBytesToHexString);
                } else {
                    BtOtaHelper.this.commonBuz(strBytesToHexString);
                }
            }
        });
    }

    public void onDisconnected(BluetoothDevice bluetoothDevice) throws IORuntimeException {
        if (this.otaListener == null) {
            throw new RuntimeException("NOT INIT EXCEPTION");
        }
        BtUtils.logBlueTooth("Setting onDisconnected " + bluetoothDevice.getName());
        BtUtils.logBlueTooth("OTA STEP:" + this.ota_step);
        if (this.ota_step != 0 && !BtUtils.isBlueEnable(this.mContext)) {
            this.deviceBean.setConnected(false);
            BtUtils.logBlueTooth("onUpGradeFail: onDisconnected 蓝牙关闭");
            this.otaListener.onUpGradeFail(13);
            return;
        }
        BtUtils.logBlueTooth("当前设备---：" + this.deviceBean.getBluetoothDevice().getAddress());
        BtUtils.logBlueTooth("断开设备---：" + bluetoothDevice.getAddress());
        BtUtils.logBlueTooth("是否为同一个---：" + BtUtils.isSameDevice(bluetoothDevice.getAddress(), this.deviceBean));
        if (BtUtils.isSameDevice(bluetoothDevice.getAddress(), this.deviceBean)) {
            this.deviceBean.setConnected(false);
            BtUtils.logBlueTooth("当前Step:" + this.ota_step);
            int i = this.ota_step;
            if (i == 2) {
                BtUtils.logBlueTooth("onDisconnected 升级完一个设备，等待另外一个回连");
                return;
            }
            if (i != 3) {
                if (i > 3) {
                    this.ota_step = 0;
                }
            } else {
                this.ota_step = 0;
                this.ota_process = 0;
                this.otaListener.onUpgradeSuccess(this.mUpInfoData.version);
                this.otaInfoDataList.clear();
                clearCachedFiles();
            }
        }
    }

    private void clearCachedFiles() throws IORuntimeException {
        setNewUpPath("");
        FileUtil.del(this.originUpPath);
        FileUtil.del(getNewUpPath());
    }

    public void onConnectSuccess(BluetoothDevice bluetoothDevice) {
        if (this.otaListener == null) {
            throw new RuntimeException("NOT INIT EXCEPTION");
        }
        if (this.deviceBean == null) {
            this.deviceBean = BtUtils.createBluetoothItem(bluetoothDevice);
        }
        if (BtUtils.isSameDevice(bluetoothDevice.getAddress(), this.deviceBean)) {
            BtUtils.logBlueTooth("OTA STEP:" + this.ota_step);
            BtUtils.logBlueTooth("Setting connected");
            this.deviceBean.setConnected(true);
            if (this.ota_step != 0) {
                this.ota_process = 0;
                this.stopCheckBattery = true;
                OtaConnectCallBack otaConnectCallBack = this.otaConnectCallBack;
                if (otaConnectCallBack != null) {
                    this.mHandler.removeCallbacks(otaConnectCallBack);
                }
                sendOtaMsg("55AA80");
                return;
            }
            this.stopCheckBattery = false;
            sendNormalMsg("C004");
            return;
        }
        this.deviceBean.setConnected(false);
        if (this.ota_step != 0) {
            this.otaListener.onConnectDiffDev();
        }
    }

    private void setNewUpPath(String str) {
        MMKV.defaultMMKV().putString("up_path", str);
    }

    private String getNewUpPath() {
        return MMKV.defaultMMKV().getString("up_path", "");
    }

    public void onSetUpFilePath(String str) {
        onSetUpFilePath(str, false);
    }

    public void onSetUpFilePath(String str, boolean z) {
        File file;
        if (TextUtils.isEmpty(str)) {
            this.otaListener.onUpGradeFail(10);
            BtUtils.logBlueTooth("onUpGradeFail: FAIL_FILE_PATH null");
            return;
        }
        this.originUpPath = str;
        if (this.deviceBean.isOtaStatus || !z) {
            String newUpPath = getNewUpPath();
            if (TextUtils.isEmpty(newUpPath)) {
                file = new File(this.originUpPath);
            } else {
                file = new File(newUpPath);
            }
            getUpInfo(file);
            return;
        }
        this.otaListener.onSyncProcess(1, 0.0d);
        this.mHandler.postDelayed(new Runnable() { // from class: com.shenju.ota.BtOtaHelper.3
            @Override // java.lang.Runnable
            public void run() {
                BtOtaHelper.this.eq_tone_address = BtOtaHelper.INDEX_START_ADDRESS;
                BtOtaHelper.this.eq_tone_length = 200;
                BtOtaHelper.this.sendDeviceEqToneCmd(BtOtaHelper.INDEX_START_ADDRESS, 200);
            }
        }, 500L);
    }

    private void getUpInfo(File file) {
        if (file == null || !file.exists()) {
            this.otaListener.onConditionFail(10);
            return;
        }
        try {
            byte[] bArr = new byte[6];
            System.arraycopy(FileUtil.readBytes(file), 0, bArr, 0, 6);
            if (!BtUtils.hexStringToString(BtUtils.bytesToHexString(bArr)).equalsIgnoreCase("CONFIG")) {
                this.otaListener.onConditionFail(10);
                return;
            }
            BtUtils.logBlueTooth("获取文件名称：" + file.getName());
            BtUtils.logBlueTooth("获取文件路径：" + file.getPath());
            BtUtils.logBlueTooth("获取文件len：" + file.length());
            BtUtils.logBlueTooth("获取文件绝对路径：" + file.getAbsolutePath());
            getOtaFileInfo(file);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void getOtaFileInfo(final File file) {
        Observable.create(new ObservableOnSubscribe<UpInfoData>() { // from class: com.shenju.ota.BtOtaHelper.5
            @Override // io.reactivex.rxjava3.core.ObservableOnSubscribe
            public void subscribe(ObservableEmitter<UpInfoData> observableEmitter) {
                try {
                    if (file.exists()) {
                        UpInfoData uploadContent = BtUtils.getUploadContent(FileUtil.readBytes(file));
                        observableEmitter.onNext(uploadContent);
                        byte[] bArr = uploadContent.upPartByteArrayWithIndex;
                        int crc = 65535;
                        int length = bArr.length % 512;
                        int length2 = length == 0 ? bArr.length / 512 : (bArr.length / 512) + 1;
                        if (length == 0) {
                            for (int i = 0; i < length2; i++) {
                                byte[] bArr2 = new byte[512];
                                System.arraycopy(bArr, i * 512, bArr2, 0, 512);
                                crc = BtUtils.getCrc(Integer.valueOf(Integer.toHexString(crc).toUpperCase(), 16).intValue(), bArr2, 512);
                            }
                        } else {
                            for (int i2 = 0; i2 < length2; i2++) {
                                if (i2 < length2 - 1) {
                                    byte[] bArr3 = new byte[512];
                                    System.arraycopy(bArr, i2 * 512, bArr3, 0, 512);
                                    crc = BtUtils.getCrc(Integer.valueOf(Integer.toHexString(crc).toUpperCase(), 16).intValue(), bArr3, 512);
                                } else {
                                    byte[] bArr4 = new byte[length];
                                    System.arraycopy(bArr, i2 * 512, bArr4, 0, length);
                                    crc = BtUtils.getCrc(Integer.valueOf(Integer.toHexString(crc).toUpperCase(), 16).intValue(), bArr4, length);
                                }
                            }
                        }
                        String strIntToHex = BtUtils.intToHex(crc);
                        String strIntToHex2 = BtUtils.intToHex(bArr.length);
                        String splitReverseHexStringCmd = BtUtils.getSplitReverseHexStringCmd(strIntToHex, 4);
                        String splitReverseHexStringCmd2 = BtUtils.getSplitReverseHexStringCmd(strIntToHex2, 4);
                        String str = "55AA82" + BtOtaHelper.this.left_right + BtUtils.intToHex((splitReverseHexStringCmd.length() + splitReverseHexStringCmd2.length()) / 2) + splitReverseHexStringCmd + splitReverseHexStringCmd2;
                        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(str);
                        char cCrc8Maxim = BtUtils.crc8Maxim(bArrHexStringToByteArray, bArrHexStringToByteArray.length);
                        BtOtaHelper.this.cmd82Array = BtUtils.hexStringToByteArray(str + BtUtils.intToHex(cCrc8Maxim));
                        BtUtils.logBlueTooth("82 完整命令：" + str + BtUtils.intToHex(cCrc8Maxim));
                        observableEmitter.onComplete();
                        return;
                    }
                    observableEmitter.onError(new Exception("No up file exception"));
                } catch (Exception e) {
                    e.printStackTrace();
                    observableEmitter.onError(e);
                }
            }
        }).subscribeOn(Schedulers.io()).observeOn(AndroidSchedulers.mainThread()).subscribe(new Observer<UpInfoData>() { // from class: com.shenju.ota.BtOtaHelper.4
            @Override // io.reactivex.rxjava3.core.Observer
            public void onSubscribe(Disposable disposable) {
                BtOtaHelper.this.disposable = disposable;
            }

            @Override // io.reactivex.rxjava3.core.Observer
            public void onNext(UpInfoData upInfoData) {
                BtOtaHelper.this.mUpInfoData = upInfoData;
                BtOtaHelper.this.otaInfoDataList.clear();
                BtOtaHelper.this.otaInfoDataList.addAll(OtaCmdConfig.packCmd83Data(upInfoData));
            }

            @Override // io.reactivex.rxjava3.core.Observer
            public void onError(Throwable th) {
                BtOtaHelper.this.otaListener.onUpFileParseFail();
            }

            @Override // io.reactivex.rxjava3.core.Observer
            public void onComplete() {
                BtUtils.logBlueTooth("固件解析结束，弹出立即升级");
                BtOtaHelper.this.mUpInfoData.upSize = FileUtil.readableFileSize(file);
                BtOtaHelper.this.otaListener.onUpFileParseSuccess(BtOtaHelper.this.mUpInfoData);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Can't fix incorrect switch cases order, some code will duplicate */
    /* JADX WARN: Removed duplicated region for block: B:7:0x0020  */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public void commonBuz(java.lang.String r17) {
        /*
            Method dump skipped, instructions count: 1544
            To view this dump add '--comments-level debug' option
        */
        throw new UnsupportedOperationException("Method not decompiled: com.shenju.ota.BtOtaHelper.commonBuz(java.lang.String):void");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendDeviceEqToneCmd(int i, int i2) {
        this.stopCheckBattery = true;
        this.otaListener.onSendMsg(OtaCmdConfig.getReadFlashCmdArray(i, i2), 1);
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Can't fix incorrect switch cases order, some code will duplicate */
    /* JADX WARN: Failed to restore switch over string. Please report as a decompilation issue */
    /* JADX WARN: Removed duplicated region for block: B:4:0x002b  */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public void otaBuz(java.lang.String r12) {
        /*
            Method dump skipped, instructions count: 516
            To view this dump add '--comments-level debug' option
        */
        throw new UnsupportedOperationException("Method not decompiled: com.shenju.ota.BtOtaHelper.otaBuz(java.lang.String):void");
    }

    private void writeInUpFile(byte[] bArr, byte[] bArr2, byte[] bArr3, String str) {
        String strReplace = str.replace(".up", "_new.up");
        BtUtils.logBlueTooth("合并前的路径:" + strReplace);
        BtUtils.logBlueTooth("合并后的路径:" + str);
        int iSavePartDataToUpFile = UParseUtil.getInstance().savePartDataToUpFile(bArr, bArr2, bArr3, str, strReplace);
        BtUtils.logBlueTooth("合并结果：" + iSavePartDataToUpFile);
        if (iSavePartDataToUpFile == 0) {
            setNewUpPath(strReplace);
            getUpInfo(new File(strReplace));
        } else {
            BtUtils.logBlueTooth("onUpGradeFail 合并文件出错");
            this.otaListener.onUpGradeFail(12);
        }
    }

    private boolean isDeviceSupportOta() {
        if (this.deviceBean.isDeviceSupportOta) {
            if (this.deviceBean.doubleDeviceStatus != 2) {
                return true;
            }
            this.otaListener.onConditionFail(4);
            return false;
        }
        this.otaListener.onConditionFail(8);
        return false;
    }

    class OtaConnectCallBack implements Runnable {
        OtaConnectCallBack() {
        }

        @Override // java.lang.Runnable
        public void run() {
            BtOtaHelper.this.otaListener.onUpGradeFail(11);
            BtUtils.logBlueTooth("onUpGradeFail 没有回连 FAIL_NOT_CONNECT_BAC");
        }
    }

    public void onDestroy() throws IORuntimeException {
        this.ota_step = 0;
        this.ota_process = 0;
        this.otaListener = null;
        this.mContext = null;
        this.deviceBean = null;
        this.mUpInfoData = null;
        this.cmd82Array = null;
        this.index = 1;
        this.otaInfoDataList.clear();
        this.otaInfoDataList = null;
        this.eqToneBean = null;
        this.sbEqData = null;
        this.sbToneData = null;
        this.stopCheckBattery = true;
        if (this.mHandler.hasCallbacks(this.otaConnectCallBack)) {
            this.mHandler.removeCallbacks(this.otaConnectCallBack);
        }
        Timer timer = this.timer;
        if (timer != null) {
            timer.cancel();
            this.timerTask = null;
            this.timer = null;
        }
        Disposable disposable = this.disposable;
        if (disposable != null) {
            disposable.dispose();
        }
        clearCachedFiles();
    }
}
