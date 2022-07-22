package com.summer.stockproject.entity;

import javax.persistence.*;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.sql.Date;

@Entity
@Table(name="amazon")
public class AAPL {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name="id")
    private int id;

    @Column(name="time_point", columnDefinition ="DATETIME")
    //@Temporal(TemporalType.TIMESTAMP)
    private Timestamp timePoint;

    @Column(name="minute_open")
    private double minuteOpen;

    @Column(name="minute_high")
    private double minuteHigh;

    @Column(name="minute_low")
    private double minuteLow;

    @Column(name="minute_close")
    private double  intminuteClose;

    @Column(name="minute_volume")
    private int minuteVolume;

    public AAPL() {

    }

    public AAPL(int id, Timestamp timePoint, double minuteOpen, double minuteHigh, double minuteLow, double intminuteClose, int minuteVolume) {
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

    public double getIntminuteClose() {
        return intminuteClose;
    }

    public void setIntminuteClose(double intminuteClose) {
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
