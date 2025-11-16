package com.summer.stockproject.entity;

import javax.persistence.*;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.sql.Date;

@Entity
@Table(name="AAPL")
public class AAPL {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name="id")
    private int id;

    @Column(name="timePoint")
    private Timestamp timePoint;

    @Column(name="minuteOpen")
    private int minuteOpen;

    @Column(name="minuteHigh")
    private int minuteHigh;

    @Column(name="minuteLow")
    private int minuteLow;

    @Column(name="minuteClose")
    private int intminuteClose;

    @Column(name="minuteVolume")
    private int minuteVolume;

    public AAPL() {

    }

    public AAPL(int id, Timestamp timePoint, int minuteOpen, int minuteHigh, int minuteLow, int intminuteClose, int minuteVolume) {
        this.id = id;
        this.timePoint = timePoint;
        this.minuteOpen = minuteOpen;
        this.minuteHigh = minuteHigh;
        this.minuteLow = minuteLow;
        this.intminuteClose = intminuteClose;
        this.minuteVolume = minuteVolume;
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public Timestamp getTimePoint() {
        return timePoint;
    }

    public void setTimePoint(Timestamp timePoint) {
        this.timePoint = timePoint;
    }

    public int getMinuteOpen() {
        return minuteOpen;
    }

    public void setMinuteOpen(int minuteOpen) {
        this.minuteOpen = minuteOpen;
    }

    public int getMinuteHigh() {
        return minuteHigh;
    }

    public void setMinuteHigh(int minuteHigh) {
        this.minuteHigh = minuteHigh;
    }

    public int getMinuteLow() {
        return minuteLow;
    }

    public void setMinuteLow(int minuteLow) {
        this.minuteLow = minuteLow;
    }

    public int getIntminuteClose() {
        return intminuteClose;
    }

    public void setIntminuteClose(int intminuteClose) {
        this.intminuteClose = intminuteClose;
    }

    public int getMinuteVolume() {
        return minuteVolume;
    }

    public void setMinuteVolume(int minuteVolume) {
        this.minuteVolume = minuteVolume;
    }

    @Override
    public String toString() {
        return "AAPL{" +
                "id=" + id +
                ", timePoint='" + timePoint + '\'' +
                ", minuteOpen=" + minuteOpen +
                ", minuteHigh=" + minuteHigh +
                ", minuteLow=" + minuteLow +
                ", intminuteClose=" + intminuteClose +
                ", minuteVolume=" + minuteVolume +
                '}';
    }
}
