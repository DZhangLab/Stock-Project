package com.summer.stockproject.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;

@Entity
@Table(name = "volatility_model_evaluation")
public class VolatilityModelEvaluation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "model_name")
    private String modelName;

    @Column(name = "eval_window_start")
    private Date evalWindowStart;

    @Column(name = "eval_window_end")
    private Date evalWindowEnd;

    @Column(name = "eval_window_days")
    private Integer evalWindowDays;

    @Column(name = "mae")
    private BigDecimal mae;

    @Column(name = "rmse")
    private BigDecimal rmse;

    @Column(name = "qlike")
    private BigDecimal qlike;

    @Column(name = "n_observations")
    private Integer nObservations;

    @Column(name = "computed_at")
    private Timestamp computedAt;

    @Column(name = "created_at")
    private Timestamp createdAt;

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

    public Date getEvalWindowStart() {
        return evalWindowStart;
    }

    public void setEvalWindowStart(Date evalWindowStart) {
        this.evalWindowStart = evalWindowStart;
    }

    public Date getEvalWindowEnd() {
        return evalWindowEnd;
    }

    public void setEvalWindowEnd(Date evalWindowEnd) {
        this.evalWindowEnd = evalWindowEnd;
    }

    public Integer getEvalWindowDays() {
        return evalWindowDays;
    }

    public void setEvalWindowDays(Integer evalWindowDays) {
        this.evalWindowDays = evalWindowDays;
    }

    public BigDecimal getMae() {
        return mae;
    }

    public void setMae(BigDecimal mae) {
        this.mae = mae;
    }

    public BigDecimal getRmse() {
        return rmse;
    }

    public void setRmse(BigDecimal rmse) {
        this.rmse = rmse;
    }

    public BigDecimal getQlike() {
        return qlike;
    }

    public void setQlike(BigDecimal qlike) {
        this.qlike = qlike;
    }

    public Integer getNObservations() {
        return nObservations;
    }

    public void setNObservations(Integer nObservations) {
        this.nObservations = nObservations;
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
}
