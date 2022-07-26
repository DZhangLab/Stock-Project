package com.summer.stockproject.graph.entity;

import javax.persistence.*;

@Entity
@Table(name="timestamptable")
public class timestamptable {

   @EmbeddedId
   private mykey mykey;

    @Column(name="minute_open")
    private double minuteOpen;

    @Column(name="minute_high", insertable = false, updatable = false)
    private double minuteHigh;

    @Column(name="minute_high")
    private double minuteLow;

    @Column(name="minute_close")
    private double minuteclose;

    @Column(name="minute_volume")
    private int minuteVolume;



    public double getMinuteOpen() {
        return minuteOpen;
    }

    public void setMinuteOpen(double minuteOpen) {
        this.minuteOpen = minuteOpen;
    }

    public double getMinuteHigh() {
        return minuteHigh;
    }

    public void setMinuteHigh(double minuteHigh) {
        this.minuteHigh = minuteHigh;
    }

    public double getMinuteLow() {
        return minuteLow;
    }

    public void setMinuteLow(double minuteLow) {
        this.minuteLow = minuteLow;
    }

    public double getMinuteclose() {
        return minuteclose;
    }

    public void setMinuteclose(double minuteclose) {
        this.minuteclose = minuteclose;
    }

    public int getMinuteVolume() {
        return minuteVolume;
    }

    public void setMinuteVolume(int minuteVolume) {
        this.minuteVolume = minuteVolume;
    }



    public mykey getMykey() {
        return mykey;
    }

    public void setMykey(com.summer.stockproject.graph.entity.mykey mykey) {
        this.mykey = mykey;
    }

    public timestamptable() {

    }

    public timestamptable(com.summer.stockproject.graph.entity.mykey mykey, double minuteOpen, double minuteHigh, double minuteLow, double minuteclose, int minuteVolume) {
        this.mykey = mykey;
        this.minuteOpen = minuteOpen;
        this.minuteHigh = minuteHigh;
        this.minuteLow = minuteLow;
        this.minuteclose = minuteclose;
        this.minuteVolume = minuteVolume;
    }

    @Override
    public String toString() {
        return "timestamptable{" +
                "mykey=" + mykey +
                ", minuteOpen=" + minuteOpen +
                ", minuteHigh=" + minuteHigh +
                ", minuteLow=" + minuteLow +
                ", minuteclose=" + minuteclose +
                ", minuteVolume=" + minuteVolume +
                '}';
    }
}


