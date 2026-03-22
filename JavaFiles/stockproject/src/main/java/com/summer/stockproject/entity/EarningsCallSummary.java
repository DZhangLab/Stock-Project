package com.summer.stockproject.entity;

import javax.persistence.*;
import java.sql.Date;
import java.sql.Timestamp;

@Entity
@Table(name = "earnings_call_summary")
public class EarningsCallSummary {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "fiscal_period_label")
    private String fiscalPeriodLabel;

    @Column(name = "call_date")
    private Date callDate;

    @Column(name = "source")
    private String source;

    @Column(name = "summary_text")
    private String summaryText;

    @Column(name = "key_takeaways_json")
    private String keyTakeawaysJson;

    @Column(name = "transcript_url")
    private String transcriptUrl;

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

    public String getFiscalPeriodLabel() {
        return fiscalPeriodLabel;
    }

    public void setFiscalPeriodLabel(String fiscalPeriodLabel) {
        this.fiscalPeriodLabel = fiscalPeriodLabel;
    }

    public Date getCallDate() {
        return callDate;
    }

    public void setCallDate(Date callDate) {
        this.callDate = callDate;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public String getSummaryText() {
        return summaryText;
    }

    public void setSummaryText(String summaryText) {
        this.summaryText = summaryText;
    }

    public String getKeyTakeawaysJson() {
        return keyTakeawaysJson;
    }

    public void setKeyTakeawaysJson(String keyTakeawaysJson) {
        this.keyTakeawaysJson = keyTakeawaysJson;
    }

    public String getTranscriptUrl() {
        return transcriptUrl;
    }

    public void setTranscriptUrl(String transcriptUrl) {
        this.transcriptUrl = transcriptUrl;
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
