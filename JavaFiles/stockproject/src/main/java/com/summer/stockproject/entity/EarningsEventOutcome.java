package com.summer.stockproject.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;

@Entity
@Table(name = "earnings_event_outcome")
public class EarningsEventOutcome {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "fiscal_period_label")
    private String fiscalPeriodLabel;

    @Column(name = "normalized_fiscal_period_label")
    private String normalizedFiscalPeriodLabel;

    @Column(name = "event_date")
    private Date eventDate;

    @Column(name = "event_date_basis")
    private String eventDateBasis;

    @Column(name = "event_release_time")
    private String eventReleaseTime;

    @Column(name = "first_reaction_date")
    private Date firstReactionDate;

    @Column(name = "pre_event_close")
    private BigDecimal preEventClose;

    @Column(name = "ret_1d")
    private BigDecimal ret1d;

    @Column(name = "ret_3d")
    private BigDecimal ret3d;

    @Column(name = "ret_5d")
    private BigDecimal ret5d;

    @Column(name = "ret_20d")
    private BigDecimal ret20d;

    @Column(name = "car_3d")
    private BigDecimal car3d;

    @Column(name = "car_5d")
    private BigDecimal car5d;

    @Column(name = "car_20d")
    private BigDecimal car20d;

    @Column(name = "surprise_pct_at_event")
    private BigDecimal surprisePctAtEvent;

    @Column(name = "ai_overall_tone_at_event")
    private String aiOverallToneAtEvent;

    @Transient
    private BigDecimal aiToneIndex;

    @Column(name = "quality_flag")
    private String qualityFlag;

    @Column(name = "exclusion_reason")
    private String exclusionReason;

    @Column(name = "computed_at")
    private Timestamp computedAt;

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

    public String getNormalizedFiscalPeriodLabel() {
        return normalizedFiscalPeriodLabel;
    }

    public void setNormalizedFiscalPeriodLabel(String normalizedFiscalPeriodLabel) {
        this.normalizedFiscalPeriodLabel = normalizedFiscalPeriodLabel;
    }

    public Date getEventDate() {
        return eventDate;
    }

    public void setEventDate(Date eventDate) {
        this.eventDate = eventDate;
    }

    public String getEventDateBasis() {
        return eventDateBasis;
    }

    public void setEventDateBasis(String eventDateBasis) {
        this.eventDateBasis = eventDateBasis;
    }

    public String getEventReleaseTime() {
        return eventReleaseTime;
    }

    public void setEventReleaseTime(String eventReleaseTime) {
        this.eventReleaseTime = eventReleaseTime;
    }

    public Date getFirstReactionDate() {
        return firstReactionDate;
    }

    public void setFirstReactionDate(Date firstReactionDate) {
        this.firstReactionDate = firstReactionDate;
    }

    public BigDecimal getPreEventClose() {
        return preEventClose;
    }

    public void setPreEventClose(BigDecimal preEventClose) {
        this.preEventClose = preEventClose;
    }

    public BigDecimal getRet1d() {
        return ret1d;
    }

    public void setRet1d(BigDecimal ret1d) {
        this.ret1d = ret1d;
    }

    public BigDecimal getRet3d() {
        return ret3d;
    }

    public void setRet3d(BigDecimal ret3d) {
        this.ret3d = ret3d;
    }

    public BigDecimal getRet5d() {
        return ret5d;
    }

    public void setRet5d(BigDecimal ret5d) {
        this.ret5d = ret5d;
    }

    public BigDecimal getRet20d() {
        return ret20d;
    }

    public void setRet20d(BigDecimal ret20d) {
        this.ret20d = ret20d;
    }

    public BigDecimal getCar3d() {
        return car3d;
    }

    public void setCar3d(BigDecimal car3d) {
        this.car3d = car3d;
    }

    public BigDecimal getCar5d() {
        return car5d;
    }

    public void setCar5d(BigDecimal car5d) {
        this.car5d = car5d;
    }

    public BigDecimal getCar20d() {
        return car20d;
    }

    public void setCar20d(BigDecimal car20d) {
        this.car20d = car20d;
    }

    public BigDecimal getSurprisePctAtEvent() {
        return surprisePctAtEvent;
    }

    public void setSurprisePctAtEvent(BigDecimal surprisePctAtEvent) {
        this.surprisePctAtEvent = surprisePctAtEvent;
    }

    public String getAiOverallToneAtEvent() {
        return aiOverallToneAtEvent;
    }

    public void setAiOverallToneAtEvent(String aiOverallToneAtEvent) {
        this.aiOverallToneAtEvent = aiOverallToneAtEvent;
    }

    public BigDecimal getAiToneIndex() {
        return aiToneIndex;
    }

    public void setAiToneIndex(BigDecimal aiToneIndex) {
        this.aiToneIndex = aiToneIndex;
    }

    public String getQualityFlag() {
        return qualityFlag;
    }

    public void setQualityFlag(String qualityFlag) {
        this.qualityFlag = qualityFlag;
    }

    public String getExclusionReason() {
        return exclusionReason;
    }

    public void setExclusionReason(String exclusionReason) {
        this.exclusionReason = exclusionReason;
    }

    public Timestamp getComputedAt() {
        return computedAt;
    }

    public void setComputedAt(Timestamp computedAt) {
        this.computedAt = computedAt;
    }
}
