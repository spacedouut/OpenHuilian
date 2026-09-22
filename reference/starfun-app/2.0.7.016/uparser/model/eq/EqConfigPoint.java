package com.shenju.uparser.model.eq;

import java.io.Serializable;

/* loaded from: classes2.dex */
public class EqConfigPoint implements Serializable, Cloneable {
    private int filter_type = 0;
    private int fc = 0;
    private float G = 0.0f;
    private float Q_factor = 0.0f;
    private boolean disable = false;
    private int itemIndex = 0;

    public int getFilter_type() {
        return this.filter_type;
    }

    public void setFilter_type(int i) {
        this.filter_type = i;
    }

    public int getFc() {
        return this.fc;
    }

    public void setFc(int i) {
        this.fc = i;
    }

    public float getG() {
        return this.G;
    }

    public void setG(float f) {
        this.G = f;
    }

    public float getQ_factor() {
        return this.Q_factor;
    }

    public void setQ_factor(float f) {
        this.Q_factor = f;
    }

    public boolean isDisable() {
        return this.disable;
    }

    public void setDisable(boolean z) {
        this.disable = z;
    }

    public int getItemIndex() {
        return this.itemIndex;
    }

    public void setItemIndex(int i) {
        this.itemIndex = i;
    }

    public String toString() {
        return "EqConfigPoint{filter_type=" + this.filter_type + ", fc=" + this.fc + ", G=" + this.G + ", Q_factor=" + this.Q_factor + ", disable=" + this.disable + ", itemIndex=" + this.itemIndex + '}';
    }

    /* renamed from: clone, reason: merged with bridge method [inline-methods] */
    public EqConfigPoint m28clone() {
        try {
            return (EqConfigPoint) super.clone();
        } catch (CloneNotSupportedException unused) {
            throw new AssertionError();
        }
    }
}
