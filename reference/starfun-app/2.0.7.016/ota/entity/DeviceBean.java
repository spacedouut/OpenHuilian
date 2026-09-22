package com.shenju.ota.entity;

import android.bluetooth.BluetoothDevice;
import android.os.Parcel;
import android.os.Parcelable;

/* loaded from: classes2.dex */
public class DeviceBean implements Parcelable {
    public static final Parcelable.Creator<DeviceBean> CREATOR = new Parcelable.Creator<DeviceBean>() { // from class: com.shenju.ota.entity.DeviceBean.1
        /* JADX WARN: Can't rename method to resolve collision */
        @Override // android.os.Parcelable.Creator
        public DeviceBean createFromParcel(Parcel parcel) {
            return new DeviceBean(parcel);
        }

        /* JADX WARN: Can't rename method to resolve collision */
        @Override // android.os.Parcelable.Creator
        public DeviceBean[] newArray(int i) {
            return new DeviceBean[i];
        }
    };
    private BluetoothDevice bluetoothDevice;
    public int doubleDeviceStatus;
    public boolean isCharging;
    public boolean isConnected;
    public boolean isDeviceSupportOta;
    public boolean isLeftConnect;
    public boolean isOtaStatus;
    public boolean isRightConnect;
    public int leftBattery;
    public String modelType;
    public String productTypeName;
    public int rightBattery;
    public String version;

    @Override // android.os.Parcelable
    public int describeContents() {
        return 0;
    }

    public String getVersion() {
        return this.version;
    }

    public void setVersion(String str) {
        this.version = str;
    }

    public String getModelType() {
        return this.modelType;
    }

    public void setModelType(String str) {
        this.modelType = str;
    }

    public String getProductTypeName() {
        return this.productTypeName;
    }

    public void setProductTypeName(String str) {
        this.productTypeName = str;
    }

    public boolean isCharging() {
        return this.isCharging;
    }

    public void setCharging(boolean z) {
        this.isCharging = z;
    }

    public boolean isDeviceSupportOta() {
        return this.isDeviceSupportOta;
    }

    public void setDeviceSupportOta(boolean z) {
        this.isDeviceSupportOta = z;
    }

    public boolean isLeftConnect() {
        return this.isLeftConnect;
    }

    public void setLeftConnect(boolean z) {
        this.isLeftConnect = z;
    }

    public boolean isRightConnect() {
        return this.isRightConnect;
    }

    public void setRightConnect(boolean z) {
        this.isRightConnect = z;
    }

    public int getLeftBattery() {
        return this.leftBattery;
    }

    public void setLeftBattery(int i) {
        this.leftBattery = i;
    }

    public int getRightBattery() {
        return this.rightBattery;
    }

    public void setRightBattery(int i) {
        this.rightBattery = i;
    }

    public boolean isOtaStatus() {
        return this.isOtaStatus;
    }

    public void setOtaStatus(boolean z) {
        this.isOtaStatus = z;
    }

    public int getDoubleDeviceStatus() {
        return this.doubleDeviceStatus;
    }

    public void setDoubleDeviceStatus(int i) {
        this.doubleDeviceStatus = i;
    }

    public boolean isConnected() {
        return this.isConnected;
    }

    public void setConnected(boolean z) {
        this.isConnected = z;
    }

    public DeviceBean() {
        this.version = "";
        this.modelType = "";
        this.productTypeName = "";
    }

    public DeviceBean(BluetoothDevice bluetoothDevice) {
        this.version = "";
        this.modelType = "";
        this.productTypeName = "";
        this.bluetoothDevice = bluetoothDevice;
    }

    public boolean getIsCharging() {
        return this.isCharging;
    }

    public void setIsCharging(boolean z) {
        this.isCharging = z;
    }

    public BluetoothDevice getBluetoothDevice() {
        return this.bluetoothDevice;
    }

    public void setBluetoothDevice(BluetoothDevice bluetoothDevice) {
        this.bluetoothDevice = bluetoothDevice;
    }

    @Override // android.os.Parcelable
    public void writeToParcel(Parcel parcel, int i) {
        parcel.writeByte(this.isCharging ? (byte) 1 : (byte) 0);
        parcel.writeByte(this.isOtaStatus ? (byte) 1 : (byte) 0);
        parcel.writeInt(this.doubleDeviceStatus);
        parcel.writeByte(this.isConnected ? (byte) 1 : (byte) 0);
        parcel.writeByte(this.isDeviceSupportOta ? (byte) 1 : (byte) 0);
        parcel.writeString(this.version);
        parcel.writeString(this.modelType);
        parcel.writeString(this.productTypeName);
        parcel.writeInt(this.leftBattery);
        parcel.writeInt(this.rightBattery);
        parcel.writeByte(this.isLeftConnect ? (byte) 1 : (byte) 0);
        parcel.writeByte(this.isRightConnect ? (byte) 1 : (byte) 0);
        parcel.writeParcelable(this.bluetoothDevice, i);
    }

    public void readFromParcel(Parcel parcel) {
        this.isCharging = parcel.readByte() != 0;
        this.isOtaStatus = parcel.readByte() != 0;
        this.doubleDeviceStatus = parcel.readInt();
        this.isConnected = parcel.readByte() != 0;
        this.isDeviceSupportOta = parcel.readByte() != 0;
        this.version = parcel.readString();
        this.modelType = parcel.readString();
        this.productTypeName = parcel.readString();
        this.leftBattery = parcel.readInt();
        this.rightBattery = parcel.readInt();
        this.isLeftConnect = parcel.readByte() != 0;
        this.isRightConnect = parcel.readByte() != 0;
        this.bluetoothDevice = (BluetoothDevice) parcel.readParcelable(BluetoothDevice.class.getClassLoader());
    }

    protected DeviceBean(Parcel parcel) {
        this.version = "";
        this.modelType = "";
        this.productTypeName = "";
        this.isCharging = parcel.readByte() != 0;
        this.isOtaStatus = parcel.readByte() != 0;
        this.doubleDeviceStatus = parcel.readInt();
        this.isConnected = parcel.readByte() != 0;
        this.isDeviceSupportOta = parcel.readByte() != 0;
        this.version = parcel.readString();
        this.modelType = parcel.readString();
        this.productTypeName = parcel.readString();
        this.leftBattery = parcel.readInt();
        this.rightBattery = parcel.readInt();
        this.isLeftConnect = parcel.readByte() != 0;
        this.isRightConnect = parcel.readByte() != 0;
        this.bluetoothDevice = (BluetoothDevice) parcel.readParcelable(BluetoothDevice.class.getClassLoader());
    }
}
