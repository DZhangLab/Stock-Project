package com.summer.stockproject.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;

/**
 * JPA entity for the daily_volatility table populated by the
 * Phase 2 daily_volatility job.  HAR-RV columns are present in
 * the schema but populated later by Phase 3 — they remain null
 * for now.
 */
@Entity
@Table(name = "daily_volatility")
public class DailyVolatility {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "as_of_date")
    private Date asOfDate;

    @Column(name = "realized_vol_5d")
    private BigDecimal realizedVol5d;

    @Column(name = "realized_vol_21d")
    private BigDecimal realizedVol21d;

    @Column(name = "realized_vol_63d")
    private BigDecimal realizedVol63d;

    @Column(name = "volatility_regime")
    private String volatilityRegime;

    @Column(name = "vol_band_low")
    private BigDecimal volBandLow;

    @Column(name = "vol_band_high")
    private BigDecimal volBandHigh;

    @Column(name = "band_hit_rate_trailing_90d")
    private BigDecimal bandHitRateTrailing90d;

    @Column(name = "har_rv_forecast_1d")
    private BigDecimal harRvForecast1d;

    @Column(name = "har_rv_model_version")
    private String harRvModelVersion;

    @Column(name = "computed_at")
    private Timestamp computedAt;

    @Column(name = "created_at")
    private Timestamp createdAt;

    @Column(name = "updated_at")
    private Timestamp updatedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public Date getAsOfDate() {
        return asOfDate;
    }

    public void setAsOfDate(Date asOfDate) {
        this.asOfDate = asOfDate;
    }

    public BigDecimal getRealizedVol5d() {
        return realizedVol5d;
    }

    public void setRealizedVol5d(BigDecimal realizedVol5d) {
        this.realizedVol5d = realizedVol5d;
    }

    public BigDecimal getRealizedVol21d() {
        return realizedVol21d;
    }

    public void setRealizedVol21d(BigDecimal realizedVol21d) {
        this.realizedVol21d = realizedVol21d;
    }

    public BigDecimal getRealizedVol63d() {
        return realizedVol63d;
    }

    public void setRealizedVol63d(BigDecimal realizedVol63d) {
        this.realizedVol63d = realizedVol63d;
    }

    public String getVolatilityRegime() {
        return volatilityRegime;
    }

    public void setVolatilityRegime(String volatilityRegime) {
        this.volatilityRegime = volatilityRegime;
    }

    public BigDecimal getVolBandLow() {
        return volBandLow;
    }

    public void setVolBandLow(BigDecimal volBandLow) {
        this.volBandLow = volBandLow;
    }

    public BigDecimal getVolBandHigh() {
        return volBandHigh;
    }

    public void setVolBandHigh(BigDecimal volBandHigh) {
        this.volBandHigh = volBandHigh;
    }

    public BigDecimal getBandHitRateTrailing90d() {
        return bandHitRateTrailing90d;
    }

    public void setBandHitRateTrailing90d(BigDecimal bandHitRateTrailing90d) {
        this.bandHitRateTrailing90d = bandHitRateTrailing90d;
    }

    public BigDecimal getHarRvForecast1d() {
        return harRvForecast1d;
    }

    public void setHarRvForecast1d(BigDecimal harRvForecast1d) {
        this.harRvForecast1d = harRvForecast1d;
    }

    public String getHarRvModelVersion() {
        return harRvModelVersion;
    }

    public void setHarRvModelVersion(String harRvModelVersion) {
        this.harRvModelVersion = harRvModelVersion;
    }

    public Timestamp getComputedAt() {
        return computedAt;
    }

    public void setComputedAt(Timestamp computedAt) {
        this.computedAt = computedAt;
    }

    public Timestamp getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Timestamp createdAt) {
        this.createdAt = createdAt;
    }

    public Timestamp getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Timestamp updatedAt) {
        this.updatedAt = updatedAt;
    }
}
