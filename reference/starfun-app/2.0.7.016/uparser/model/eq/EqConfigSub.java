package com.shenju.uparser.model.eq;

import java.util.Map;
import java.util.TreeMap;

/* loaded from: classes2.dex */
public class EqConfigSub {
    private float compensationGain;
    private int pageTypeId;
    private Map<Integer, EqConfigPoint> pointSettingMap = new TreeMap();

    public float getCompensationGain() {
        return this.compensationGain;
    }

    public void setCompensationGain(float f) {
        this.compensationGain = f;
    }

    public int getPageTypeId() {
        return this.pageTypeId;
    }

    public void setPageTypeId(int i) {
        this.pageTypeId = i;
    }

    public Map<Integer, EqConfigPoint> getPointSettingMap() {
        return this.pointSettingMap;
    }

    public void setPointSettingMap(Map<Integer, EqConfigPoint> map) {
        this.pointSettingMap = map;
    }

    public String toString() {
        return "EqConfigSub{pageTypeId=" + this.pageTypeId + ", compensationGain=" + this.compensationGain + ", pointSettingMap=" + this.pointSettingMap + '}';
    }
}
