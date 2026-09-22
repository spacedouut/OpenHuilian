package com.sjbt.base.ui;

import android.bluetooth.BluetoothDevice;
import android.content.ComponentName;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.ServiceConnection;
import android.net.Uri;
import android.os.Bundle;
import android.os.IBinder;
import android.text.TextUtils;
import android.view.KeyEvent;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.core.content.FileProvider;
import cn.hutool.core.io.FileUtil;
import cn.hutool.core.io.IORuntimeException;
import cn.hutool.core.text.CharSequenceUtil;
import cn.hutool.core.util.ArrayUtil;
import com.alibaba.idst.nui.Constants;
import com.gyf.immersionbar.ImmersionBar;
import com.mobile.mobilehardware.base.BaseData;
import com.shenju.ota.OtaCmdConfig;
import com.shenju.ota.entity.OtaInfoData;
import com.shenju.ota.entity.UpInfoData;
import com.shenju.ota.utils.BtUtils;
import com.shenju.ota.utils.UParseUtil;
import com.sjbt.base.BaseActivity;
import com.sjbt.base.BaseApplication;
import com.sjbt.base.Config;
import com.sjbt.base.R;
import com.sjbt.base.bt.BtBase;
import com.sjbt.base.bt.BtClient;
import com.sjbt.base.bt.BtReceiver;
import com.sjbt.base.bt.CMDConfig;
import com.sjbt.base.bt.OnBTStateListener;
import com.sjbt.base.entity.DevInfo;
import com.sjbt.base.entity.DeviceBean;
import com.sjbt.base.entity.EqToneBean;
import com.sjbt.base.entity.OtaVersionInfo;
import com.sjbt.base.log.LogUtil;
import com.sjbt.base.service.OtaService;
import com.sjbt.base.utils.LocalDataManager;
import com.sjbt.base.utils.UriUtil;
import com.sjbt.base.widget.CallBack;
import com.sjbt.base.widget.ToastUtil;
import com.sjbt.base.widget.UploadDialog;
import com.sjbt.lib_common.utils.FileUtils;
import com.sjbt.lib_common.utils.SystemUtil;
import io.reactivex.rxjava3.android.schedulers.AndroidSchedulers;
import io.reactivex.rxjava3.core.Observable;
import io.reactivex.rxjava3.core.ObservableEmitter;
import io.reactivex.rxjava3.core.ObservableOnSubscribe;
import io.reactivex.rxjava3.core.Observer;
import io.reactivex.rxjava3.disposables.Disposable;
import io.reactivex.rxjava3.schedulers.Schedulers;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Objects;
import java.util.Timer;
import java.util.TimerTask;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/* loaded from: classes2.dex */
public class SettingMoreActivity extends BaseActivity implements BtBase.Listener, OnBTStateListener, View.OnClickListener, IOtaView, InfoView {
    private static final int CELL_BYTE_LENGTH = 512;
    private static final long CLICK_TIMEOUT = 3000;
    private static final int CMD_82_BYTE_LENGTH = 4;
    private static final int GET_FLASH_LENGTH = 100;
    private static final int LATEST_OTA_SUPPORT = 220408;
    private static final int LATEST_OTA_SUPPORT_FOR_A10 = 220411;
    private static final int MAX_ERR_COUNT = 6;
    private static final String OTA_EQ2P = "EQ2P";
    private static final int OTA_LOWEST_BATTERY = 50;
    private static final int OTA_LOWEST_PHONE_BATTERY = 30;
    private static final int OTA_STEP_ONE = 1;
    private static final int OTA_STEP_THREE = 3;
    private static final int OTA_STEP_TWO = 2;
    private static final String OTA_TONE = "TONE";
    private static final int REQUIRED_CLICKS = 10;
    private byte[] cmd82Array;
    private DeviceBean deviceBean;
    private Disposable disposable;
    private InfoPresenter infoPresenter;
    private boolean isLocalUpgrade;
    private ImageView ivBack;
    private LinearLayout layoutCloudVersion;
    private LinearLayout layoutGyro;
    private LinearLayout layoutMacAddress;
    private LinearLayout layout_local_version;
    private BtReceiver mBtReceiver;
    private OtaService mOtaService;
    private UpInfoData mUpInfoData;
    private String originUpPath;
    private OtaConnectCallBack otaConnectCallBack;
    private OtaPresenter otaPresenter;
    private int ota_step;
    private int retryConnectCount;
    private Timer timer;
    private TimerTask timerTask;
    private TextView tvMacAddress;
    private TextView tvModelName;
    private TextView tvVersionName;
    private TextView tv_core_model;
    private TextView tv_product_date;
    private TextView tv_product_factory;
    private UploadDialog uploadDialog;
    private OtaVersionInfo versionInfo;
    private int ota_process = 0;
    private List<OtaInfoData> otaInfoDataList = new ArrayList();
    private int otaTimeOutErrCount = 0;
    private String left_right = "11";
    private int phoneBattery = 50;
    private boolean supportOta = true;
    private boolean canUpdateOta = true;
    private boolean stopCheckBattery = false;
    private boolean isFront = false;
    private boolean isProcessing = false;
    private BtClient mClient = BtClient.getInstance(this);
    private String zipPath = "";
    private int clickCount = 0;
    private long lastClickTime = 0;
    private final ServiceConnection mServiceConnection = new ServiceConnection() { // from class: com.sjbt.base.ui.SettingMoreActivity.25
        @Override // android.content.ServiceConnection
        public void onServiceConnected(ComponentName componentName, IBinder iBinder) {
            SettingMoreActivity.this.mOtaService = ((OtaService.LocalBinder) iBinder).getService();
            LogUtil.logCommon("onServiceConnected " + SettingMoreActivity.this.mOtaService);
        }

        @Override // android.content.ServiceConnection
        public void onServiceDisconnected(ComponentName componentName) {
            LogUtil.logCommon("onServiceDisconnected");
            SettingMoreActivity.this.mOtaService = null;
        }
    };
    private EqToneBean eqToneBean = new EqToneBean();
    private StringBuffer sbEqData = new StringBuffer();
    private StringBuffer sbToneData = new StringBuffer();
    private int index = 1;
    private int INDEX_START_ADDRESS = 12288;
    private int INDEX_LENGTH = 200;
    private int eq_tone_address = 12288;
    private int eq_tone_length = 200;

    @Override // com.sjbt.base.bt.OnBTStateListener
    public void onFoundDevice(BluetoothDevice bluetoothDevice) {
    }

    @Override // com.sjbt.base.bt.OnBTStateListener
    public void onStateChanged(BluetoothDevice bluetoothDevice) {
    }

    @Override // com.sjbt.base.BaseActivity, androidx.appcompat.app.AppCompatActivity, androidx.fragment.app.FragmentActivity, androidx.activity.ComponentActivity, androidx.core.app.ComponentActivity, android.app.Activity
    protected void onCreate(Bundle bundle) throws NoSuchMethodException, SecurityException {
        super.onCreate(bundle);
        getWindow().setFlags(128, 128);
        setContentView(R.layout.activity_more);
        ImmersionBar.with(this).statusBarDarkFont(true).statusBarColor(R.color.color_f6f7f9).fitsSystemWindows(true).init();
        this.otaPresenter = new OtaPresenter(this);
        this.infoPresenter = new InfoPresenter(this);
        this.mBtReceiver = new BtReceiver(this, this);
        this.ivBack = (ImageView) findViewById(R.id.iv_back);
        this.tvModelName = (TextView) findViewById(R.id.tv_model_name);
        this.tvVersionName = (TextView) findViewById(R.id.tv_version_name);
        this.tvMacAddress = (TextView) findViewById(R.id.tv_mac_address);
        this.tv_core_model = (TextView) findViewById(R.id.tv_core_model);
        this.tv_product_factory = (TextView) findViewById(R.id.tv_product_factory);
        this.tv_product_date = (TextView) findViewById(R.id.tv_product_date);
        this.layoutGyro = (LinearLayout) findViewById(R.id.layout_gyro);
        this.layoutCloudVersion = (LinearLayout) findViewById(R.id.layout_version);
        this.layout_local_version = (LinearLayout) findViewById(R.id.layout_local_version);
        this.layoutMacAddress = (LinearLayout) findViewById(R.id.layout_mac_address);
        this.ivBack.setOnClickListener(this);
        this.tvModelName.setOnClickListener(this);
        this.tvMacAddress.setOnClickListener(this);
        this.layoutCloudVersion.setOnClickListener(this);
        this.layout_local_version.setOnClickListener(this);
        this.layoutMacAddress.setOnClickListener(this);
        findViewById(R.id.layout_share_log).setOnClickListener(this);
        this.tvModelName.setOnClickListener(new View.OnClickListener() { // from class: com.sjbt.base.ui.SettingMoreActivity.1
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                long jCurrentTimeMillis = System.currentTimeMillis();
                if (jCurrentTimeMillis - SettingMoreActivity.this.lastClickTime > SettingMoreActivity.CLICK_TIMEOUT) {
                    SettingMoreActivity.this.clickCount = 0;
                }
                SettingMoreActivity.this.clickCount++;
                SettingMoreActivity.this.lastClickTime = jCurrentTimeMillis;
                if (SettingMoreActivity.this.clickCount >= 10) {
                    SettingMoreActivity.this.findViewById(R.id.layout_share_log).setVisibility(0);
                    SettingMoreActivity.this.clickCount = 0;
                    SettingMoreActivity.this.lastClickTime = 0L;
                }
            }
        });
        this.deviceBean = (DeviceBean) getIntent().getParcelableExtra(Config.TAG_DEVICE);
        startOtaService();
        DeviceBean deviceBean = this.deviceBean;
        if (deviceBean != null) {
            this.tvMacAddress.setText(deviceBean.getBluetoothDevice().getAddress());
            this.tvVersionName.setText(this.deviceBean.getVersion_05());
            this.tv_core_model.setText(this.deviceBean.chipModel_03);
            UploadDialog uploadDialog = new UploadDialog(this, 1, new CallBack<Integer>() { // from class: com.sjbt.base.ui.SettingMoreActivity.2
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Integer num) {
                    int iIntValue = num.intValue();
                    if (iIntValue == 2) {
                        SettingMoreActivity.this.mClient.clearMsgQueue();
                        SettingMoreActivity.this.ota_step = 1;
                        SettingMoreActivity.this.stopCheckBattery = true;
                        SettingMoreActivity.this.ota_process = 0;
                        SettingMoreActivity settingMoreActivity = SettingMoreActivity.this;
                        settingMoreActivity.showLoadingDlg(settingMoreActivity.getString(R.string.ota_preparing));
                        SettingMoreActivity.this.uploadDialog.showVerifyingDialog();
                        SettingMoreActivity.this.sendOtaMsg("55AA80");
                        HashMap map = new HashMap();
                        map.put("current_version", SettingMoreActivity.this.deviceBean.getVersion_05());
                        SettingMoreActivity.this.statisticEvents(map, "start_upgrade_up");
                    }
                    switch (iIntValue) {
                        case 5:
                            SettingMoreActivity.this.mClient.clearMsgQueue();
                            if (SettingMoreActivity.this.isPhoneConditionSatisfied()) {
                                LocalDataManager.getInstance().setNewUpPath("");
                                SettingMoreActivity.this.sendNormalMsg("C013");
                                break;
                            }
                            break;
                        case 6:
                            SettingMoreActivity.this.mClient.clearMsgQueue();
                            if (SettingMoreActivity.this.uploadDialog != null) {
                                SettingMoreActivity.this.uploadDialog.dismiss();
                            }
                            SettingMoreActivity.this.otaInfoDataList.clear();
                            HashMap map2 = new HashMap();
                            if (SettingMoreActivity.this.mUpInfoData != null) {
                                map2.put("new_version", SettingMoreActivity.this.mUpInfoData.version);
                            }
                            SettingMoreActivity.this.statisticEvents(map2, "upgrade_success");
                            break;
                        case 7:
                            SettingMoreActivity.this.uploadDialog.resetDialog();
                            break;
                        case 8:
                            if (SettingMoreActivity.this.versionInfo != null) {
                                HashMap map3 = new HashMap();
                                map3.put("current_version", SettingMoreActivity.this.deviceBean.getVersion_05());
                                SettingMoreActivity.this.statisticEvents(map3, "start_download_apk");
                                SettingMoreActivity.this.stopCheckBattery = true;
                                SettingMoreActivity.this.otaPresenter.downloadApk(SettingMoreActivity.this, Config.APP_DOWNLOAD_PATH + SettingMoreActivity.this.versionInfo.getVersion() + ".up", SettingMoreActivity.this.versionInfo);
                                SettingMoreActivity.this.uploadDialog.updateDownLoadUpProgress(0.0d);
                                break;
                            }
                            break;
                        case 9:
                            SettingMoreActivity.this.hideLoadingDlg();
                            break;
                    }
                }
            });
            this.uploadDialog = uploadDialog;
            uploadDialog.setOnDismissListener(new DialogInterface.OnDismissListener() { // from class: com.sjbt.base.ui.SettingMoreActivity.3
                @Override // android.content.DialogInterface.OnDismissListener
                public void onDismiss(DialogInterface dialogInterface) {
                }
            });
            this.mClient.clearMsgQueue();
            LogUtil.logBlueTooth(getLocalClassName() + " 进入设备连接蓝牙");
            connectDevice(this.deviceBean.getBluetoothDevice());
        }
        this.timer = new Timer();
        TimerTask timerTask = new TimerTask() { // from class: com.sjbt.base.ui.SettingMoreActivity.4
            @Override // java.util.TimerTask, java.lang.Runnable
            public void run() {
                if (SettingMoreActivity.this.isFront && SettingMoreActivity.this.deviceBean.isConnected && !SettingMoreActivity.this.stopCheckBattery) {
                    SettingMoreActivity.this.sendNormalMsg("C009");
                }
            }
        };
        this.timerTask = timerTask;
        this.timer.scheduleAtFixedRate(timerTask, 300L, 2000L);
    }

    private void destroyService() {
        try {
            if (this.mOtaService != null) {
                unbindService(this.mServiceConnection);
                this.mOtaService.onDestroy();
                this.mOtaService = null;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private int getPhoneBattery() {
        Intent intentRegisterReceiver = getApplicationContext().registerReceiver(null, new IntentFilter("android.intent.action.BATTERY_CHANGED"));
        this.phoneBattery = intentRegisterReceiver.getIntExtra(BaseData.Signal.LEVEL, 0);
        intentRegisterReceiver.getIntExtra("status", 0);
        intentRegisterReceiver.getIntExtra(BaseData.Battery.HEALTH, 1);
        intentRegisterReceiver.getBooleanExtra(BaseData.Battery.PRESENT, false);
        intentRegisterReceiver.getIntExtra("scale", 0);
        intentRegisterReceiver.getIntExtra("plugged", 0);
        intentRegisterReceiver.getIntExtra(BaseData.Battery.VOLTAGE, 0);
        intentRegisterReceiver.getIntExtra(BaseData.Battery.TEMPERATURE, 0);
        intentRegisterReceiver.getStringExtra(BaseData.Battery.TECHNOLOGY);
        return this.phoneBattery;
    }

    private void chooseFile() {
        Intent intent = new Intent("android.intent.action.GET_CONTENT");
        intent.addCategory("android.intent.category.OPENABLE");
        intent.setType("*/*");
        startActivityForResult(Intent.createChooser(intent, getString(R.string.choose_file)), 100);
    }

    @Override // com.sjbt.base.ui.InfoView
    public void getInfo(DevInfo devInfo) {
        if (TextUtils.isEmpty(devInfo.model)) {
            setUI(getModelType(), this.tvModelName);
        } else {
            setUI(devInfo.model, this.tvModelName);
        }
        setUI(devInfo.business_name, this.tv_product_factory);
        HashMap map = new HashMap();
        map.put("channel_name", devInfo.business_name);
        map.put("product_id", devInfo.productId);
        map.put("product_model", devInfo.model);
        statisticEvents(map, "channel");
    }

    @Override // com.sjbt.base.ui.InfoView
    public void getInfoFail() {
        setNoInternetOrTimeOut();
    }

    private void getOtaFileInfo(final File file) {
        Observable.create(new ObservableOnSubscribe<UpInfoData>() { // from class: com.sjbt.base.ui.SettingMoreActivity.6
            @Override // io.reactivex.rxjava3.core.ObservableOnSubscribe
            public void subscribe(ObservableEmitter<UpInfoData> observableEmitter) {
                try {
                    if (file.exists()) {
                        UpInfoData uploadContent = BtUtils.getUploadContent(FileUtils.getByteStream(file));
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
                        String splitReverseHexStringCmd = SettingMoreActivity.this.getSplitReverseHexStringCmd(strIntToHex, 4);
                        String splitReverseHexStringCmd2 = SettingMoreActivity.this.getSplitReverseHexStringCmd(strIntToHex2, 4);
                        String str = "55AA82" + SettingMoreActivity.this.left_right + BtUtils.intToHex((splitReverseHexStringCmd.length() + splitReverseHexStringCmd2.length()) / 2) + splitReverseHexStringCmd + splitReverseHexStringCmd2;
                        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(str);
                        char cCrc8Maxim = BtUtils.crc8Maxim(bArrHexStringToByteArray, bArrHexStringToByteArray.length);
                        SettingMoreActivity.this.cmd82Array = BtUtils.hexStringToByteArray(str + BtUtils.intToHex(cCrc8Maxim));
                        observableEmitter.onComplete();
                        return;
                    }
                    SettingMoreActivity settingMoreActivity = SettingMoreActivity.this;
                    settingMoreActivity.showToast(settingMoreActivity.getString(R.string.firm_not_exist));
                    observableEmitter.onError(new Exception("No up file exception"));
                } catch (Exception e) {
                    e.printStackTrace();
                    observableEmitter.onError(e);
                }
            }
        }).subscribeOn(Schedulers.io()).observeOn(AndroidSchedulers.mainThread()).subscribe(new Observer<UpInfoData>() { // from class: com.sjbt.base.ui.SettingMoreActivity.5
            @Override // io.reactivex.rxjava3.core.Observer
            public void onSubscribe(Disposable disposable) {
                SettingMoreActivity.this.disposable = disposable;
            }

            @Override // io.reactivex.rxjava3.core.Observer
            public void onNext(UpInfoData upInfoData) {
                SettingMoreActivity.this.mUpInfoData = upInfoData;
                SettingMoreActivity.this.packCmd83Data(upInfoData);
            }

            @Override // io.reactivex.rxjava3.core.Observer
            public void onError(Throwable th) {
                SettingMoreActivity.this.showToast(th.getMessage());
            }

            @Override // io.reactivex.rxjava3.core.Observer
            public void onComplete() {
                LogUtil.logBlueTooth("固件解析结束，弹出立即升级");
                SettingMoreActivity.this.mUpInfoData.upSize = FileUtil.readableFileSize(file);
                SettingMoreActivity.this.mHandler.postDelayed(new Runnable() { // from class: com.sjbt.base.ui.SettingMoreActivity.5.1
                    @Override // java.lang.Runnable
                    public void run() {
                        SettingMoreActivity.this.uploadDialog.showStartUpgradeUp(SettingMoreActivity.this.mUpInfoData);
                    }
                }, 1000L);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Removed duplicated region for block: B:13:0x0033  */
    /* JADX WARN: Removed duplicated region for block: B:17:? A[RETURN, SYNTHETIC] */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public void connectDevice(android.bluetooth.BluetoothDevice r5) throws java.lang.NoSuchMethodException, java.lang.SecurityException {
        /*
            r4 = this;
            com.sjbt.base.bt.BtClient r0 = r4.mClient
            r0.setListener(r4)
            java.lang.Class<android.bluetooth.BluetoothDevice> r0 = android.bluetooth.BluetoothDevice.class
            java.lang.String r1 = "isConnected"
            r2 = 0
            r3 = r2
            java.lang.Class[] r3 = (java.lang.Class[]) r3     // Catch: java.lang.reflect.InvocationTargetException -> L22 java.lang.IllegalAccessException -> L27 java.lang.NoSuchMethodException -> L2c
            java.lang.reflect.Method r0 = r0.getDeclaredMethod(r1, r3)     // Catch: java.lang.reflect.InvocationTargetException -> L22 java.lang.IllegalAccessException -> L27 java.lang.NoSuchMethodException -> L2c
            r1 = 1
            r0.setAccessible(r1)     // Catch: java.lang.reflect.InvocationTargetException -> L22 java.lang.IllegalAccessException -> L27 java.lang.NoSuchMethodException -> L2c
            java.lang.Object[] r2 = (java.lang.Object[]) r2     // Catch: java.lang.reflect.InvocationTargetException -> L22 java.lang.IllegalAccessException -> L27 java.lang.NoSuchMethodException -> L2c
            java.lang.Object r0 = r0.invoke(r5, r2)     // Catch: java.lang.reflect.InvocationTargetException -> L22 java.lang.IllegalAccessException -> L27 java.lang.NoSuchMethodException -> L2c
            java.lang.Boolean r0 = (java.lang.Boolean) r0     // Catch: java.lang.reflect.InvocationTargetException -> L22 java.lang.IllegalAccessException -> L27 java.lang.NoSuchMethodException -> L2c
            boolean r0 = r0.booleanValue()     // Catch: java.lang.reflect.InvocationTargetException -> L22 java.lang.IllegalAccessException -> L27 java.lang.NoSuchMethodException -> L2c
            goto L31
        L22:
            r0 = move-exception
            r0.printStackTrace()
            goto L30
        L27:
            r0 = move-exception
            r0.printStackTrace()
            goto L30
        L2c:
            r0 = move-exception
            r0.printStackTrace()
        L30:
            r0 = 0
        L31:
            if (r0 == 0) goto L38
            com.sjbt.base.bt.BtClient r0 = r4.mClient
            r0.connect(r5)
        L38:
            return
        */
        throw new UnsupportedOperationException("Method not decompiled: com.sjbt.base.ui.SettingMoreActivity.connectDevice(android.bluetooth.BluetoothDevice):void");
    }

    @Override // android.view.View.OnClickListener
    public void onClick(View view) {
        if (view.equals(this.ivBack)) {
            disConnectPage();
            finish();
            return;
        }
        if (view.getId() == this.layoutMacAddress.getId()) {
            return;
        }
        if (view.equals(this.layoutCloudVersion)) {
            this.isLocalUpgrade = false;
            HashMap map = new HashMap();
            map.put("current_version", this.deviceBean.getVersion_05());
            statisticEvents(map, "check_cloud_version");
            if (isPhoneConditionSatisfied()) {
                LogUtil.logBlueTooth("检查云端版本 showLoadingDlg");
                showLoadingDlg();
                LogUtil.logBlueTooth("发送：C013");
                sendNormalMsg("C013");
                return;
            }
            return;
        }
        if (view.equals(this.layout_local_version)) {
            this.isLocalUpgrade = true;
            if (isPhoneConditionSatisfied()) {
                showLoadingDlg();
                sendNormalMsg("C013");
                return;
            }
            return;
        }
        if (view.getId() == R.id.layout_share_log) {
            StringBuilder sb = new StringBuilder();
            File externalFilesDir = getExternalFilesDir(null);
            Objects.requireNonNull(externalFilesDir);
            sb.append(externalFilesDir.getAbsolutePath());
            sb.append(File.separator);
            sb.append(getString(R.string.app_name));
            sb.append(File.separator);
            sb.append("log");
            String string = sb.toString();
            this.zipPath = getFilesDir().getAbsolutePath() + File.separator + getString(R.string.app_name) + "-log-" + System.currentTimeMillis() + ".zip";
            if (zipFolders(new File(this.zipPath), new File(string))) {
                Uri uriForFile = FileProvider.getUriForFile(this, "com.fun.app.provider", new File(this.zipPath));
                Intent intent = new Intent("android.intent.action.SEND");
                intent.setType("application/zip");
                intent.putExtra("android.intent.extra.STREAM", uriForFile);
                intent.putExtra("android.intent.extra.SUBJECT", "share log file");
                startActivityForResult(Intent.createChooser(intent, "Share via"), Config.SHARE_LOG);
                return;
            }
            showToast("Failed to create zip file for sharing log");
        }
    }

    private boolean zipFolders(File file, File file2) throws IOException {
        try {
            ZipOutputStream zipOutputStream = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(file)));
            try {
                if (!file2.isDirectory()) {
                    System.out.println(file2.getAbsolutePath() + " is not a directory. Skipping.");
                }
                zipFolderRecursive(file2, "", zipOutputStream);
                zipOutputStream.close();
                return true;
            } catch (Throwable th) {
                zipOutputStream.close();
                throw th;
            }
        } catch (IOException e) {
            e.printStackTrace();
            return false;
        }
    }

    private void zipFolderRecursive(File file, String str, ZipOutputStream zipOutputStream) throws IOException {
        File[] fileArrListFiles = file.listFiles();
        if (fileArrListFiles == null) {
            return;
        }
        for (File file2 : fileArrListFiles) {
            String name = str.isEmpty() ? file2.getName() : str + File.separator + file2.getName();
            if (file2.isDirectory()) {
                zipFolderRecursive(file2, name, zipOutputStream);
            } else {
                FileInputStream fileInputStream = new FileInputStream(file2);
                BufferedInputStream bufferedInputStream = new BufferedInputStream(fileInputStream);
                try {
                    zipOutputStream.putNextEntry(new ZipEntry(name));
                    byte[] bArr = new byte[8192];
                    while (true) {
                        int i = bufferedInputStream.read(bArr);
                        if (i == -1) {
                            break;
                        } else {
                            zipOutputStream.write(bArr, 0, i);
                        }
                    }
                    zipOutputStream.closeEntry();
                } finally {
                    bufferedInputStream.close();
                    fileInputStream.close();
                }
            }
        }
    }

    private void disConnectPage() {
        this.mClient.clearMsgQueue();
        this.mClient.closeSocket(getLocalClassName());
    }

    /* JADX INFO: Access modifiers changed from: private */
    public String getSplitReverseHexStringCmd(String str, int i) {
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

    @Override // androidx.fragment.app.FragmentActivity, android.app.Activity
    protected void onActivityResult(int i, int i2, Intent intent) throws IORuntimeException {
        super.onActivityResult(i, i2, intent);
        if (intent == null || intent.getData() == null) {
            return;
        }
        if (!isBlueEnable()) {
            showConfirmDialogWithCallback(getString(R.string.device_closed), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.7
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Object obj) {
                    SettingMoreActivity.this.toPhoneSetting();
                }
            });
            this.deviceBean.setConnected(false);
            return;
        }
        LogUtil.logBlueTooth("onActivityResult");
        if (i != 100) {
            if (i != 112 && i == 10101) {
                FileUtil.del(this.zipPath);
                return;
            }
            return;
        }
        this.originUpPath = UriUtil.getFileAbsolutePath(BaseApplication.getInstance(), intent.getData());
        LogUtil.logCommon("文件真实路径：" + this.originUpPath);
        String newUpPath = LocalDataManager.getInstance().getNewUpPath();
        if (this.deviceBean.isOtaStatus_11 && !TextUtils.isEmpty(newUpPath)) {
            getUpInfo(newUpPath);
            return;
        }
        showLoadingDlg(getString(R.string.preparing));
        int i3 = this.INDEX_START_ADDRESS;
        this.eq_tone_address = i3;
        int i4 = this.INDEX_LENGTH;
        this.eq_tone_length = i4;
        sendDeviceEqToneCmd(i3, i4);
    }

    /* JADX WARN: Can't fix incorrect switch cases order, some code will duplicate */
    /* JADX WARN: Failed to restore switch over string. Please report as a decompilation issue */
    /* JADX WARN: Removed duplicated region for block: B:15:0x005d  */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    private void msgTimeOut(byte[] r10) {
        /*
            Method dump skipped, instructions count: 458
            To view this dump add '--comments-level debug' option
        */
        throw new UnsupportedOperationException("Method not decompiled: com.sjbt.base.ui.SettingMoreActivity.msgTimeOut(byte[]):void");
    }

    @Override // com.sjbt.base.bt.OnBTStateListener
    public void onNewDeviceConnect(final BluetoothDevice bluetoothDevice) {
        LogUtil.logBlueTooth("新增设备:" + bluetoothDevice.getAddress());
        if (isSameDevice(bluetoothDevice, this.deviceBean)) {
            LogUtil.logBlueTooth("新增设备-设备回调");
            this.mHandler.postDelayed(new Runnable() { // from class: com.sjbt.base.ui.SettingMoreActivity.11
                @Override // java.lang.Runnable
                public void run() throws NoSuchMethodException, SecurityException {
                    SettingMoreActivity.this.connectDevice(bluetoothDevice);
                }
            }, 2000L);
        }
    }

    private void connectSuccess(BluetoothDevice bluetoothDevice) {
        if (isSameDevice(bluetoothDevice, this.deviceBean)) {
            LogUtil.logBlueTooth("OTA STEP:" + this.ota_step);
            LogUtil.logBlueTooth("Setting connected");
            this.deviceBean.setConnected(true);
            if (this.ota_step != 0) {
                this.ota_process = 0;
                this.stopCheckBattery = true;
                sendOtaMsg("55AA80");
                if (this.otaConnectCallBack != null) {
                    this.mHandler.removeCallbacks(this.otaConnectCallBack);
                    return;
                }
                return;
            }
            this.stopCheckBattery = false;
            sendNormalMsg(CMDConfig.CMD_READ_CHIP_MODEL_03);
            return;
        }
        this.deviceBean.setConnected(false);
        LogUtil.logBlueTooth("蓝牙连接状态4:" + this.deviceBean.isConnected);
        if (this.ota_step != 0) {
            showOtaStatusDialogWithCallback(R.mipmap.icon_update_fail_2, "", getString(R.string.connect_other_device), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.12
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Object obj) {
                    SettingMoreActivity.this.finish();
                }
            });
        }
    }

    @Override // com.sjbt.base.bt.OnBTStateListener
    public void onDisconnected(BluetoothDevice bluetoothDevice) throws IORuntimeException {
        UploadDialog uploadDialog;
        LogUtil.logBlueTooth("Setting onDisconnected " + bluetoothDevice.getName());
        LogUtil.logBlueTooth("OTA STEP:" + this.ota_step);
        if (!isBlueEnable()) {
            this.ota_process = 0;
            showConfirmDialogWithCallback(getString(R.string.device_closed), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.13
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Object obj) {
                    SettingMoreActivity.this.toPhoneSetting();
                }
            });
            return;
        }
        if (this.ota_step != 0 && !isBlueEnable()) {
            this.deviceBean.setConnected(false);
            LogUtil.logBlueTooth("蓝牙连接状态5:" + this.deviceBean.isConnected);
            UploadDialog uploadDialog2 = this.uploadDialog;
            if (uploadDialog2 != null && uploadDialog2.isShowing()) {
                this.uploadDialog.dismiss();
            }
            showOtaStatusDialogWithCallback(R.mipmap.icon_phone_bt_open, "", getString(R.string.open_bt), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.14
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Object obj) {
                    SettingMoreActivity.this.toPhoneSetting();
                }
            });
            return;
        }
        LogUtil.logBlueTooth("当前设备---：" + this.deviceBean.getBluetoothDevice().getAddress());
        LogUtil.logBlueTooth("断开设备---：" + bluetoothDevice.getAddress());
        LogUtil.logBlueTooth("是否为同一个---：" + isSameDevice(bluetoothDevice, this.deviceBean));
        if (isSameDevice(bluetoothDevice, this.deviceBean)) {
            this.deviceBean.setConnected(false);
            LogUtil.logBlueTooth("蓝牙连接状态6:" + this.deviceBean.isConnected);
            LogUtil.logBlueTooth("当前Step:" + this.ota_step);
            int i = this.ota_step;
            if (i == 2) {
                if (this.uploadDialog == null || isFinishing()) {
                    return;
                }
                LogUtil.logBlueTooth("onDisconnected updateProgress OTA_STEP_TWO:" + this.ota_step);
                this.uploadDialog.updateProgress(getString(this.left_right.equals("11") ? R.string.right_ear : R.string.left_ear), 0.0d);
                return;
            }
            if (i != 3) {
                if (i <= 3 || (uploadDialog = this.uploadDialog) == null || !uploadDialog.isShowing()) {
                    return;
                }
                this.uploadDialog.dismiss();
                return;
            }
            if (this.uploadDialog == null || isFinishing()) {
                return;
            }
            this.uploadDialog.showFinishDialog(6, this.deviceBean.getVersion_05(), this.mUpInfoData.version);
            this.ota_step = 0;
            this.ota_process = 0;
            this.mClient.clearMsgQueue();
            FileUtil.del(this.originUpPath);
            FileUtil.del(LocalDataManager.getInstance().getNewUpPath());
            LocalDataManager.getInstance().setNewUpPath("");
        }
    }

    private boolean isSameDevice(BluetoothDevice bluetoothDevice, DeviceBean deviceBean) {
        if (bluetoothDevice == null || deviceBean == null || deviceBean.getBluetoothDevice() == null || TextUtils.isEmpty(bluetoothDevice.getAddress()) || TextUtils.isEmpty(deviceBean.getBluetoothDevice().getAddress())) {
            return false;
        }
        return bluetoothDevice.getAddress().equals(deviceBean.getBluetoothDevice().getAddress());
    }

    @Override // com.sjbt.base.bt.BtBase.Listener
    public void onConnectFailed(BluetoothDevice bluetoothDevice, String str) {
        LogUtil.logBlueTooth("OTA蓝牙连接失败:" + str);
        if (!isBlueEnable()) {
            showConfirmDialogWithCallback(getString(R.string.device_closed), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.15
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Object obj) {
                    SettingMoreActivity.this.toPhoneSetting();
                }
            });
            return;
        }
        if (isSameDevice(bluetoothDevice, this.deviceBean)) {
            this.deviceBean.setConnected(false);
            LogUtil.logBlueTooth("蓝牙连接状态11:" + this.deviceBean.isConnected);
        }
        if (str.contains("socket might closed")) {
            int i = this.retryConnectCount;
            if (i < 5) {
                this.retryConnectCount = i + 1;
                LogUtil.logBlueTooth(getLocalClassName() + " socket might closed 重连");
                retryConnect(bluetoothDevice);
                return;
            }
            this.retryConnectCount = 0;
            showConfirmDialogWithCallback("", "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.16
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Object obj) {
                    SettingMoreActivity.this.finish();
                }
            });
            return;
        }
        if (str.contains("Connection reset by peer")) {
            LogUtil.logBlueTooth(getLocalClassName() + " Connection reset by peer 重连");
            retryConnect(bluetoothDevice);
        }
    }

    private void retryConnect(final BluetoothDevice bluetoothDevice) {
        showLoadingDlg();
        LogUtil.logBlueTooth(getLocalClassName() + " retryConnect showLoadingDlg");
        this.mHandler.postDelayed(new Runnable() { // from class: com.sjbt.base.ui.SettingMoreActivity.17
            @Override // java.lang.Runnable
            public void run() throws NoSuchMethodException, SecurityException {
                SettingMoreActivity.this.connectDevice(bluetoothDevice);
            }
        }, 1000L);
    }

    /* JADX WARN: Can't fix incorrect switch cases order, some code will duplicate */
    /* JADX WARN: Failed to restore switch over string. Please report as a decompilation issue */
    /* JADX WARN: Removed duplicated region for block: B:4:0x0053  */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    private void otaBuz(java.lang.String r13) {
        /*
            Method dump skipped, instructions count: 556
            To view this dump add '--comments-level debug' option
        */
        throw new UnsupportedOperationException("Method not decompiled: com.sjbt.base.ui.SettingMoreActivity.otaBuz(java.lang.String):void");
    }

    class OtaConnectCallBack implements Runnable {
        OtaConnectCallBack() {
        }

        @Override // java.lang.Runnable
        public void run() {
            SettingMoreActivity.this.showOtaStatusDialogWithCallback(R.mipmap.icon_update_fail_2, SettingMoreActivity.this.getString(R.string.upgrade_fail), SettingMoreActivity.this.getString(R.string.wait_3_seconds), SettingMoreActivity.this.getString(R.string.submit), new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.OtaConnectCallBack.1
                @Override // com.sjbt.base.widget.CallBack
                public void callBack(Object obj) {
                    SettingMoreActivity.this.finish();
                }
            });
        }
    }

    private byte[] getOtaCmd(String str) {
        byte[] bArrHexStringToByteArray = BtUtils.hexStringToByteArray(str);
        return BtUtils.hexStringToByteArray(str + BtUtils.intToHex(BtUtils.crc8Maxim(bArrHexStringToByteArray, bArrHexStringToByteArray.length)));
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void packCmd83Data(UpInfoData upInfoData) {
        String str;
        String str2;
        int i;
        this.otaInfoDataList.clear();
        byte[] bArr = upInfoData.upPartByteArrayWithOutIndex;
        LogUtil.logBlueTooth("升级区数据:");
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
                addOtaData(i8, "55AA83", getSplitReverseHexStringCmd(BtUtils.intToHex(i4), i5), getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.firmwarePosition + i9), i7), getSplitReverseHexStringCmd(BtUtils.intToHex(i2), i7), BtUtils.bytesToHexString(bArr3));
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
            String str6 = str3;
            int length3 = bArr2.length;
            String strBytesToHexString = BtUtils.bytesToHexString(bArr2);
            String splitReverseHexStringCmd = getSplitReverseHexStringCmd(BtUtils.intToHex(length3 + 8), 2);
            String splitReverseHexStringCmd2 = getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.indexPosition), 4);
            String splitReverseHexStringCmd3 = getSplitReverseHexStringCmd(BtUtils.intToHex(length3), 4);
            LogUtil.logBlueTooth(str5 + splitReverseHexStringCmd + str6 + splitReverseHexStringCmd2 + " dataLength:" + splitReverseHexStringCmd3);
            addOtaData(i3 + 1, "55AA83", splitReverseHexStringCmd, splitReverseHexStringCmd2, splitReverseHexStringCmd3, strBytesToHexString);
            return;
        }
        String str7 = "索引部分 length：";
        String str8 = " offset:";
        int i10 = 2;
        int i11 = 4;
        int i12 = 0;
        while (i12 < i3) {
            if (i12 < i3 - 1) {
                byte[] bArr4 = new byte[512];
                int i13 = i12 * 512;
                System.arraycopy(bArr, i13, bArr4, 0, 512);
                String str9 = str8;
                str2 = str7;
                str = str9;
                i = i12;
                addOtaData(i12, "55AA83", getSplitReverseHexStringCmd(BtUtils.intToHex(520), i10), getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.firmwarePosition + i13), i11), getSplitReverseHexStringCmd(BtUtils.intToHex(512), i11), BtUtils.bytesToHexString(bArr4));
            } else {
                str = str8;
                str2 = str7;
                i = i12;
                byte[] bArr5 = new byte[length];
                int i14 = i * 512;
                System.arraycopy(bArr, i14, bArr5, 0, length);
                addOtaData(i, "55AA83", getSplitReverseHexStringCmd(BtUtils.intToHex(length + 8), 2), getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.firmwarePosition + i14), 4), getSplitReverseHexStringCmd(BtUtils.intToHex(length), 4), BtUtils.bytesToHexString(bArr5));
            }
            i12 = i + 1;
            str7 = str2;
            str8 = str;
            i10 = 2;
            i11 = 4;
        }
        String strBytesToHexString2 = BtUtils.bytesToHexString(bArr2);
        String splitReverseHexStringCmd4 = getSplitReverseHexStringCmd(BtUtils.intToHex(bArr2.length + 8), 2);
        String splitReverseHexStringCmd5 = getSplitReverseHexStringCmd(BtUtils.intToHex(upInfoData.indexPosition), 4);
        String splitReverseHexStringCmd6 = getSplitReverseHexStringCmd(BtUtils.intToHex(bArr2.length), 4);
        LogUtil.logBlueTooth(str7 + splitReverseHexStringCmd4 + str8 + splitReverseHexStringCmd5 + " dataLength:" + splitReverseHexStringCmd6);
        addOtaData(i3 + 1, "55AA83", splitReverseHexStringCmd4, splitReverseHexStringCmd5, splitReverseHexStringCmd6, strBytesToHexString2);
    }

    private void addOtaData(int i, String str, String str2, String str3, String str4, String str5) {
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
        this.otaInfoDataList.add(otaInfoData);
    }

    @Override // com.sjbt.base.BaseActivity, androidx.appcompat.app.AppCompatActivity, androidx.fragment.app.FragmentActivity, android.app.Activity
    protected void onDestroy() {
        super.onDestroy();
        Disposable disposable = this.disposable;
        if (disposable != null) {
            disposable.dispose();
        }
        UploadDialog uploadDialog = this.uploadDialog;
        if (uploadDialog != null) {
            uploadDialog.dismiss();
            this.uploadDialog = null;
        }
        unregisterReceiver(this.mBtReceiver);
        destroyService();
        this.timer.cancel();
        this.timer = null;
    }

    @Override // android.app.Activity
    protected void onRestart() {
        super.onRestart();
        LogUtil.logBlueTooth(getLocalClassName() + " onRestart " + this.ota_step);
        if (!SystemUtil.isForeground(this, getLocalClassName()) || isBlueEnable()) {
            return;
        }
        showConfirmDialogWithCallback(getString(R.string.device_closed), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.22
            @Override // com.sjbt.base.widget.CallBack
            public void callBack(Object obj) {
                SettingMoreActivity.this.toPhoneSetting();
            }
        });
        this.deviceBean.setConnected(false);
        LogUtil.logBlueTooth("蓝牙连接状态2:" + this.deviceBean.isConnected);
    }

    @Override // androidx.fragment.app.FragmentActivity, android.app.Activity
    protected void onResume() {
        super.onResume();
        this.isFront = true;
    }

    @Override // androidx.fragment.app.FragmentActivity, android.app.Activity
    protected void onPause() {
        super.onPause();
        hideLoadingDlg();
        this.isFront = false;
    }

    @Override // androidx.appcompat.app.AppCompatActivity, androidx.fragment.app.FragmentActivity, android.app.Activity
    protected void onStop() {
        super.onStop();
        LogUtil.logBlueTooth(getLocalClassName() + " onStop()");
        hideLoadingDlg();
        setResult(-1);
        this.isFront = false;
    }

    @Override // androidx.appcompat.app.AppCompatActivity, android.app.Activity, android.view.KeyEvent.Callback
    public boolean onKeyDown(int i, KeyEvent keyEvent) {
        if (i == 4) {
            LogUtil.logBlueTooth("onKeyDown:KEYCODE_BACK closeSocket");
            disConnectPage();
        }
        return super.onKeyDown(i, keyEvent);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean isPhoneConditionSatisfied() {
        if (isVersionOk()) {
            if (getPhoneBattery() > 30) {
                if (isBlueEnable()) {
                    if (this.deviceBean.isConnected) {
                        if (this.deviceBean.isLeftConnect && this.deviceBean.isRightConnect) {
                            if (this.deviceBean.getLeftBattery() >= 50 && this.deviceBean.getRightBattery() >= 50) {
                                if (!this.deviceBean.isCharging) {
                                    if (this.canUpdateOta) {
                                        return true;
                                    }
                                    showOtaStatusDialogWithCallback(R.mipmap.icon_update_none, "", getString(R.string.no_need_update), "", null);
                                    return false;
                                }
                                showOtaStatusDialogWithCallback(R.mipmap.icon_ear_phone_outside, "", getString(R.string.keep_both_outside), "", null);
                                return false;
                            }
                            showOtaStatusDialogWithCallback(R.mipmap.icon_ear_phone_battery, "", getString(R.string.device_battery_50), "", null);
                            return false;
                        }
                        showOtaStatusDialogWithCallback(R.mipmap.icon_ear_phone_outside, "", getString(R.string.keep_both_outside), "", null);
                        return false;
                    }
                    LogUtil.logBlueTooth("keep_device_connect 1");
                    showOtaStatusDialogWithCallback(R.mipmap.icon_bt_connect, "", getString(R.string.keep_device_connect), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.23
                        @Override // com.sjbt.base.widget.CallBack
                        public void callBack(Object obj) {
                            SettingMoreActivity.this.toPhoneSetting();
                        }
                    });
                    return false;
                }
                showOtaStatusDialogWithCallback(R.mipmap.icon_phone_bt_open, "", getString(R.string.open_phone_bt), "", new CallBack() { // from class: com.sjbt.base.ui.SettingMoreActivity.24
                    @Override // com.sjbt.base.widget.CallBack
                    public void callBack(Object obj) {
                        SettingMoreActivity.this.toPhoneSetting();
                    }
                });
                return false;
            }
            showOtaStatusDialogWithCallback(R.mipmap.icon_phone_battery, "", getString(R.string.phone_battery_over_30), "", null);
            return false;
        }
        showOtaStatusDialogWithCallback(R.mipmap.icon_update_none, "", getString(R.string.no_need_update), "", null);
        return false;
    }

    private boolean isVersionOk() throws NumberFormatException {
        DeviceBean deviceBean = this.deviceBean;
        if (deviceBean == null || TextUtils.isEmpty(deviceBean.version_05) || TextUtils.isEmpty(this.deviceBean.proModel_04)) {
            return false;
        }
        String str = this.deviceBean.version_05;
        if (TextUtils.isEmpty(str) || str.length() < 7) {
            return false;
        }
        long j = Long.parseLong(str.substring(0, 6));
        LogUtil.logBlueTooth("当前版本日期：" + j);
        return this.deviceBean.proModel_04.replaceAll(CharSequenceUtil.SPACE, "").toLowerCase().equals("a10") ? j > 220411 : j > 220408;
    }

    private boolean isDeviceSupportOta() {
        if (this.supportOta) {
            if (this.deviceBean.doubleDeviceStatus_12 != 2) {
                return true;
            }
            showOtaStatusDialogWithCallback(R.mipmap.icon_ear_phone_outside, "", getString(R.string.keep_both_outside), "", null);
            return false;
        }
        showOtaStatusDialogWithCallback(R.mipmap.icon_update_fail_2, "", getString(R.string.not_support_ota), "", null);
        return false;
    }

    private void startOtaService() {
        Intent intent = new Intent(this, (Class<?>) OtaService.class);
        bindService(intent, this.mServiceConnection, 1);
        startService(intent);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendOtaMsg(String str) {
        this.stopCheckBattery = true;
        this.mClient.sendBytes(getOtaCmd(str + this.left_right + "00"), 3);
    }

    private void sendOtaBytes(String str) {
        this.stopCheckBattery = true;
        this.mClient.sendBytes(BtUtils.hexStringToByteArray(str), 3);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendNormalMsg(String str) {
        this.mClient.sendBytes(BtUtils.hexStringToByteArray(str), 1);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendDeviceEqToneCmd(int i, int i2) {
        this.stopCheckBattery = true;
        this.mClient.sendBytes(CMDConfig.getReadFlashCmdArray(i, i2), 1);
    }

    /* JADX WARN: Can't fix incorrect switch cases order, some code will duplicate */
    /* JADX WARN: Removed duplicated region for block: B:7:0x0024  */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    private void updateUi(java.lang.String r17) {
        /*
            Method dump skipped, instructions count: 1932
            To view this dump add '--comments-level debug' option
        */
        throw new UnsupportedOperationException("Method not decompiled: com.sjbt.base.ui.SettingMoreActivity.updateUi(java.lang.String):void");
    }

    private void resetEqTone() {
        this.index = 1;
        this.eq_tone_address = this.INDEX_START_ADDRESS;
        this.eq_tone_length = this.INDEX_LENGTH;
        this.stopCheckBattery = false;
        this.mClient.clearMsgQueue();
        this.eqToneBean.indexArray = null;
        this.eqToneBean.eqData = null;
        this.eqToneBean.toneData = null;
        StringBuffer stringBuffer = this.sbToneData;
        stringBuffer.delete(0, stringBuffer.length());
        StringBuffer stringBuffer2 = this.sbEqData;
        stringBuffer2.delete(0, stringBuffer2.length());
    }

    private void setNoInternetOrTimeOut() {
        setUI(getModelType(), this.tvModelName);
        setUI("", this.tv_product_factory);
    }

    private String getModelType() {
        if (this.deviceBean.proModel_04.contains(".")) {
            return this.deviceBean.proModel_04.split("\\.")[0];
        }
        return this.deviceBean.proModel_04;
    }

    private void setUI(final String str, final TextView textView) {
        runOnUiThread(new Runnable() { // from class: com.sjbt.base.ui.SettingMoreActivity.26
            @Override // java.lang.Runnable
            public void run() {
                textView.setText(str);
            }
        });
    }

    private void writeInUpFile(byte[] bArr, byte[] bArr2, byte[] bArr3, String str) {
        String strReplace = str.replace(".up", "_new.up");
        LogUtil.logBlueTooth("new:" + strReplace);
        LogUtil.logBlueTooth("old:" + str);
        int iSavePartDataToUpFile = UParseUtil.getInstance().savePartDataToUpFile(bArr, bArr2, bArr3, str, strReplace);
        LogUtil.logBlueTooth("合并结果：" + iSavePartDataToUpFile);
        hideLoadingDlg();
        LogUtil.logBlueTooth("hideLoadingDlg-正常");
        if (iSavePartDataToUpFile == 0) {
            LocalDataManager.getInstance().setNewUpPath(strReplace);
            getUpInfo(strReplace);
        } else {
            showOtaStatusDialogWithCallback(R.mipmap.icon_update_fail_2, "", getString(R.string.upgrade_fail), "", null);
        }
    }

    @Override // com.sjbt.base.ui.IOtaView
    public void downloadProcess(final int i) {
        runOnUiThread(new Runnable() { // from class: com.sjbt.base.ui.SettingMoreActivity.27
            @Override // java.lang.Runnable
            public void run() {
                SettingMoreActivity.this.uploadDialog.updateDownLoadUpProgress(i);
            }
        });
    }

    @Override // com.sjbt.base.ui.IOtaView
    public void downloadSuccess(String str) {
        this.originUpPath = str;
        String newUpPath = LocalDataManager.getInstance().getNewUpPath();
        if (this.deviceBean.isOtaStatus_11 && !TextUtils.isEmpty(newUpPath)) {
            getUpInfo(newUpPath);
        } else {
            showLoadingDlg(getString(R.string.preparing));
            this.mHandler.postDelayed(new Runnable() { // from class: com.sjbt.base.ui.SettingMoreActivity.28
                @Override // java.lang.Runnable
                public void run() {
                    SettingMoreActivity settingMoreActivity = SettingMoreActivity.this;
                    settingMoreActivity.eq_tone_address = settingMoreActivity.INDEX_START_ADDRESS;
                    SettingMoreActivity settingMoreActivity2 = SettingMoreActivity.this;
                    settingMoreActivity2.eq_tone_length = settingMoreActivity2.INDEX_LENGTH;
                    SettingMoreActivity.this.mClient.clearMsgQueue();
                    SettingMoreActivity settingMoreActivity3 = SettingMoreActivity.this;
                    settingMoreActivity3.sendDeviceEqToneCmd(settingMoreActivity3.INDEX_START_ADDRESS, SettingMoreActivity.this.INDEX_LENGTH);
                }
            }, 1500L);
        }
    }

    private void getUpInfo(String str) {
        File file = new File(str);
        if (!file.exists()) {
            LogUtil.logBlueTooth("异常1");
            showToast(getString(R.string.error_up_file));
            return;
        }
        if (file.length() < 100) {
            LogUtil.logBlueTooth("异常2");
            showToast(getString(R.string.error_up_file));
            return;
        }
        String fileExtension = com.blankj.utilcode.util.FileUtils.getFileExtension(file);
        if (!TextUtils.isEmpty(fileExtension) && !fileExtension.equals("up")) {
            LogUtil.logBlueTooth("异常3");
            showToast(getString(R.string.error_up_file));
            return;
        }
        try {
            byte[] bArr = new byte[6];
            System.arraycopy(FileUtils.getByteStream(file), 0, bArr, 0, 6);
            if (!BtUtils.hexStringToString(BtUtils.bytesToHexString(bArr)).equalsIgnoreCase("CONFIG")) {
                LogUtil.logBlueTooth("异常4");
                showToast(getString(R.string.error_up_file));
            } else {
                getOtaFileInfo(file);
            }
        } catch (Exception e) {
            e.printStackTrace();
            LogUtil.logBlueTooth("异常5");
            showToast(getString(R.string.error_up_file));
        }
    }

    @Override // com.sjbt.base.ui.IOtaView
    public void downloadFail(String str) {
        hideLoadingDlg();
        LogUtil.logBlueTooth("hideLoadingDlg-111");
        showToast(getString(R.string.download_fail_tip));
    }

    @Override // com.sjbt.base.ui.IOtaView
    public void noNeedUpgrade() {
        hideLoadingDlg();
        ToastUtil.showToast(getString(R.string.no_need_update));
    }

    @Override // com.sjbt.base.ui.IOtaView
    public void onGetUpVersionInfo(OtaVersionInfo otaVersionInfo) {
        this.versionInfo = otaVersionInfo;
        hideLoadingDlg();
        if (!this.deviceBean.getVersion_05().equals(otaVersionInfo.getVersion())) {
            if (isFinishing()) {
                return;
            }
            this.uploadDialog.showNewUpDialog(otaVersionInfo);
            return;
        }
        ToastUtil.showToast(getString(R.string.no_need_update));
    }

    @Override // com.sjbt.base.bt.BtBase.Listener
    public void socketNotify(int i, Object obj) {
        if (isDestroyed()) {
            return;
        }
        if (i == 0) {
            LogUtil.logBlueTooth("连接断开");
            return;
        }
        if (i == 1) {
            hideLoadingDlg();
            BluetoothDevice bluetoothDevice = (BluetoothDevice) obj;
            LogUtil.logBlueTooth(String.format("与%s(%s)连接成功", bluetoothDevice.getName(), bluetoothDevice.getAddress()));
            this.mClient.clearMsgQueue();
            connectSuccess(bluetoothDevice);
            return;
        }
        if (i != 2) {
            if (i != 3) {
                return;
            }
            msgTimeOut((byte[]) obj);
            return;
        }
        String string = obj.toString();
        LogUtil.logBlueTooth("返回消息: " + string);
        try {
            if (string.startsWith(OtaCmdConfig.HEAD_OTA_UPPER) || string.startsWith(OtaCmdConfig.HEAD_OTA_LOW)) {
                otaBuz(string);
            } else {
                updateUi(string);
            }
        } catch (Exception e) {
            e.printStackTrace();
            LogUtil.logBlueTooth("通信命令返回异常:" + e.getMessage());
            showToast(getString(R.string.excetion_in_ota_process));
        }
    }
}
