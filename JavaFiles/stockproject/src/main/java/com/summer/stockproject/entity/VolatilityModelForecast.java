package com.summer.stockproject.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;

@Entity
@Table(name = "volatility_model_forecast")
public class VolatilityModelForecast {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "model_name")
    private String modelName;

    @Column(name = "as_of_date")
    private Date asOfDate;

    @Column(name = "target_date")
    private Date targetDate;

    @Column(name = "forecast_vol_annualized")
    private BigDecimal forecastVolAnnualized;

    @Column(name = "forecast_variance")
    private BigDecimal forecastVariance;

    @Column(name = "actual_vol_annualized")
    private BigDecimal actualVolAnnualized;

    @Column(name = "actual_variance")
    private BigDecimal actualVariance;

    @Column(name = "model_version")
    private String modelVersion;

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

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public Date getAsOfDate() {
        return asOfDate;
    }

    public void setAsOfDate(Date asOfDate) {
        this.asOfDate = asOfDate;
    }

    public Date getTargetDate() {
        return targetDate;
    }

    public void setTargetDate(Date targetDate) {
        this.targetDate = targetDate;
    }

    public BigDecimal getForecastVolAnnualized() {
        return forecastVolAnnualized;
    }

    public void setForecastVolAnnualized(BigDecimal forecastVolAnnualized) {
        this.forecastVolAnnualized = forecastVolAnnualized;
    }

    public BigDecimal getForecastVariance() {
        return forecastVariance;
    }

    public void setForecastVariance(BigDecimal forecastVariance) {
        this.forecastVariance = forecastVariance;
    }

    public BigDecimal getActualVolAnnualized() {
        return actualVolAnnualized;
    }

    public void setActualVolAnnualized(BigDecimal actualVolAnnualized) {
        this.actualVolAnnualized = actualVolAnnualized;
    }

    public BigDecimal getActualVariance() {
        return actualVariance;
    }

    public void setActualVariance(BigDecimal actualVariance) {
        this.actualVariance = actualVariance;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
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
