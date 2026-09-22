package com.shenju.uparser.model.eq;

/* loaded from: classes2.dex */
public class Eq2ItemData {
    private float data;
    private int extend;
    private int itemIndex;
    private int pageId;
    private int type;

    public Eq2ItemData() {
        this.pageId = 0;
        this.itemIndex = 0;
        this.type = 0;
        this.extend = 0;
        this.data = 0.0f;
    }

    public Eq2ItemData(int i, int i2) {
        this.pageId = i;
        this.itemIndex = i2;
        this.type = 0;
        this.extend = 0;
        this.data = 0.0f;
    }

    public Eq2ItemData(int i, int i2, float f) {
        this.pageId = i;
        this.itemIndex = i2;
        this.type = 0;
        this.extend = 0;
        this.data = f;
    }

    public int getPageId() {
        return this.pageId;
    }

    public void setPageId(int i) {
        this.pageId = i;
    }

    public int getType() {
        return this.type;
    }

    public void setType(int i) {
        this.type = i;
    }

    public int getItemIndex() {
        return this.itemIndex;
    }

    public void setItemIndex(int i) {
        this.itemIndex = i;
    }

    public int getExtend() {
        return this.extend;
    }

    public void setExtend(int i) {
        this.extend = i;
    }

    public float getData() {
        return this.data;
    }

    public void setData(float f) {
        this.data = f;
    }
}
