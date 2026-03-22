package com.summer.stockproject.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;

@Entity
@Table(name = "quarterly_reporting_snapshot")
public class QuarterlyReportingSnapshot {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "fiscal_date_ending")
    private Date fiscalDateEnding;

    @Column(name = "reported_date")
    private Date reportedDate;

    @Column(name = "fiscal_period_label")
    private String fiscalPeriodLabel;

    @Column(name = "reported_currency")
    private String reportedCurrency;

    @Column(name = "total_revenue")
    private BigDecimal totalRevenue;

    @Column(name = "gross_profit")
    private BigDecimal grossProfit;

    @Column(name = "operating_income")
    private BigDecimal operatingIncome;

    @Column(name = "net_income")
    private BigDecimal netIncome;

    @Column(name = "reported_eps")
    private BigDecimal reportedEps;

    @Column(name = "estimated_eps")
    private BigDecimal estimatedEps;

    @Column(name = "surprise")
    private BigDecimal surprise;

    @Column(name = "surprise_percentage")
    private BigDecimal surprisePercentage;

    @Column(name = "source")
    private String source;

    @Column(name = "raw_payload_json")
    private String rawPayloadJson;

    @Column(name = "updated_at")
    private Timestamp updatedAt;

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

    public Date getFiscalDateEnding() {
        return fiscalDateEnding;
    }

    public void setFiscalDateEnding(Date fiscalDateEnding) {
        this.fiscalDateEnding = fiscalDateEnding;
    }

    public Date getReportedDate() {
        return reportedDate;
    }

    public void setReportedDate(Date reportedDate) {
        this.reportedDate = reportedDate;
    }

    public String getFiscalPeriodLabel() {
        return fiscalPeriodLabel;
    }

    public void setFiscalPeriodLabel(String fiscalPeriodLabel) {
        this.fiscalPeriodLabel = fiscalPeriodLabel;
    }

    public String getReportedCurrency() {
        return reportedCurrency;
    }

    public void setReportedCurrency(String reportedCurrency) {
        this.reportedCurrency = reportedCurrency;
    }

    public BigDecimal getTotalRevenue() {
        return totalRevenue;
    }

    public void setTotalRevenue(BigDecimal totalRevenue) {
        this.totalRevenue = totalRevenue;
    }

    public BigDecimal getGrossProfit() {
        return grossProfit;
    }

    public void setGrossProfit(BigDecimal grossProfit) {
        this.grossProfit = grossProfit;
    }

    public BigDecimal getOperatingIncome() {
        return operatingIncome;
    }

    public void setOperatingIncome(BigDecimal operatingIncome) {
        this.operatingIncome = operatingIncome;
    }

    public BigDecimal getNetIncome() {
        return netIncome;
    }

    public void setNetIncome(BigDecimal netIncome) {
        this.netIncome = netIncome;
    }

    public BigDecimal getReportedEps() {
        return reportedEps;
    }

    public void setReportedEps(BigDecimal reportedEps) {
        this.reportedEps = reportedEps;
    }

    public BigDecimal getEstimatedEps() {
        return estimatedEps;
    }

    public void setEstimatedEps(BigDecimal estimatedEps) {
        this.estimatedEps = estimatedEps;
    }

    public BigDecimal getSurprise() {
        return surprise;
    }

    public void setSurprise(BigDecimal surprise) {
        this.surprise = surprise;
    }

    public BigDecimal getSurprisePercentage() {
        return surprisePercentage;
    }

    public void setSurprisePercentage(BigDecimal surprisePercentage) {
        this.surprisePercentage = surprisePercentage;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public String getRawPayloadJson() {
        return rawPayloadJson;
    }

    public void setRawPayloadJson(String rawPayloadJson) {
        this.rawPayloadJson = rawPayloadJson;
    }

    public Timestamp getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Timestamp updatedAt) {
        this.updatedAt = updatedAt;
    }

    public Timestamp getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Timestamp createdAt) {
        this.createdAt = createdAt;
    }
}
