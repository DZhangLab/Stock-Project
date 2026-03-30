package com.summer.stockproject.entity;

import javax.persistence.*;
import java.sql.Date;
import java.sql.Timestamp;

@Entity
@Table(name = "company_news_ai_summary")
public class CompanyNewsAiSummary {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "analysis_date")
    private Date analysisDate;

    @Column(name = "source_window_label")
    private String sourceWindowLabel;

    @Column(name = "source_news_count")
    private Integer sourceNewsCount;

    @Column(name = "overall_sentiment_label")
    private String overallSentimentLabel;

    @Column(name = "overall_sentiment_summary")
    private String overallSentimentSummary;

    @Column(name = "main_themes_json")
    private String mainThemesJson;

    @Column(name = "top_positive_driver")
    private String topPositiveDriver;

    @Column(name = "top_risk_concern")
    private String topRiskConcern;

    @Column(name = "confidence_note")
    private String confidenceNote;

    @Column(name = "provider")
    private String provider;

    @Column(name = "model_name")
    private String modelName;

    @Column(name = "prompt_version")
    private String promptVersion;

    @Column(name = "source_articles_json")
    private String sourceArticlesJson;

    @Column(name = "raw_model_response_json")
    private String rawModelResponseJson;

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

    public Date getAnalysisDate() {
        return analysisDate;
    }

    public void setAnalysisDate(Date analysisDate) {
        this.analysisDate = analysisDate;
    }

    public String getSourceWindowLabel() {
        return sourceWindowLabel;
    }

    public void setSourceWindowLabel(String sourceWindowLabel) {
        this.sourceWindowLabel = sourceWindowLabel;
    }

    public Integer getSourceNewsCount() {
        return sourceNewsCount;
    }

    public void setSourceNewsCount(Integer sourceNewsCount) {
        this.sourceNewsCount = sourceNewsCount;
    }

    public String getOverallSentimentLabel() {
        return overallSentimentLabel;
    }

    public void setOverallSentimentLabel(String overallSentimentLabel) {
        this.overallSentimentLabel = overallSentimentLabel;
    }

    public String getOverallSentimentSummary() {
        return overallSentimentSummary;
    }

    public void setOverallSentimentSummary(String overallSentimentSummary) {
        this.overallSentimentSummary = overallSentimentSummary;
    }

    public String getMainThemesJson() {
        return mainThemesJson;
    }

    public void setMainThemesJson(String mainThemesJson) {
        this.mainThemesJson = mainThemesJson;
    }

    public String getTopPositiveDriver() {
        return topPositiveDriver;
    }

    public void setTopPositiveDriver(String topPositiveDriver) {
        this.topPositiveDriver = topPositiveDriver;
    }

    public String getTopRiskConcern() {
        return topRiskConcern;
    }

    public void setTopRiskConcern(String topRiskConcern) {
        this.topRiskConcern = topRiskConcern;
    }

    public String getConfidenceNote() {
        return confidenceNote;
    }

    public void setConfidenceNote(String confidenceNote) {
        this.confidenceNote = confidenceNote;
    }

    public String getProvider() {
        return provider;
    }

    public void setProvider(String provider) {
        this.provider = provider;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getPromptVersion() {
        return promptVersion;
    }

    public void setPromptVersion(String promptVersion) {
        this.promptVersion = promptVersion;
    }

    public String getSourceArticlesJson() {
        return sourceArticlesJson;
    }

    public void setSourceArticlesJson(String sourceArticlesJson) {
        this.sourceArticlesJson = sourceArticlesJson;
    }

    public String getRawModelResponseJson() {
        return rawModelResponseJson;
    }

    public void setRawModelResponseJson(String rawModelResponseJson) {
        this.rawModelResponseJson = rawModelResponseJson;
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
