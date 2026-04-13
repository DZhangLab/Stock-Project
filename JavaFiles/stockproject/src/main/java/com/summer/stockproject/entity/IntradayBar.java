package com.summer.stockproject.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.sql.Timestamp;

@Entity
@Table(name="AAPL")
public class IntradayBar {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name="id")
    private int id;

    @Column(name="timePoint")
    private Timestamp timePoint;

    @Column(name="minuteOpen")
    private BigDecimal minuteOpen;

    @Column(name="minuteHigh")
    private BigDecimal minuteHigh;

    @Column(name="minuteLow")
    private BigDecimal minuteLow;

    @Column(name="minuteClose")
    private BigDecimal minuteClose;

    @Column(name="minuteVolume")
    private Double minuteVolume;

    public IntradayBar() {

    }

    public IntradayBar(int id, Timestamp timePoint, BigDecimal minuteOpen, BigDecimal minuteHigh, BigDecimal minuteLow, BigDecimal minuteClose, Double minuteVolume) {
        this.id = id;
        this.timePoint = timePoint;
        this.minuteOpen = minuteOpen;
        this.minuteHigh = minuteHigh;
        this.minuteLow = minuteLow;
        this.minuteClose = minuteClose;
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

    public BigDecimal getMinuteOpen() {
        return minuteOpen;
    }

    public void setMinuteOpen(BigDecimal minuteOpen) {
        this.minuteOpen = minuteOpen;
    }

    public BigDecimal getMinuteHigh() {
        return minuteHigh;
    }

    public void setMinuteHigh(BigDecimal minuteHigh) {
        this.minuteHigh = minuteHigh;
    }

    public BigDecimal getMinuteLow() {
        return minuteLow;
    }

    public void setMinuteLow(BigDecimal minuteLow) {
        this.minuteLow = minuteLow;
    }

    public BigDecimal getMinuteClose() {
        return minuteClose;
    }

    public void setMinuteClose(BigDecimal minuteClose) {
        this.minuteClose = minuteClose;
    }

    public Double getMinuteVolume() {
        return minuteVolume;
    }

    public void setMinuteVolume(Double minuteVolume) {
        this.minuteVolume = minuteVolume;
    }

    @Override
    public String toString() {
        return "IntradayBar{" +
                "id=" + id +
                ", timePoint='" + timePoint + '\'' +
                ", minuteOpen=" + minuteOpen +
                ", minuteHigh=" + minuteHigh +
                ", minuteLow=" + minuteLow +
                ", minuteClose=" + minuteClose +
                ", minuteVolume=" + minuteVolume +
                '}';
    }
}
