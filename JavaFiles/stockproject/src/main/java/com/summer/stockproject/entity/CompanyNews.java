package com.summer.stockproject.entity;

import javax.persistence.*;
import java.math.BigDecimal;
import java.sql.Timestamp;

@Entity
@Table(name = "company_news")
public class CompanyNews {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "symbol")
    private String symbol;

    @Column(name = "title")
    private String title;

    @Column(name = "summary")
    private String summary;

    @Column(name = "url")
    private String url;

    @Column(name = "url_hash")
    private String urlHash;

    @Column(name = "source")
    private String source;

    @Column(name = "published_at")
    private Timestamp publishedAt;

    @Column(name = "av_overall_sentiment_score")
    private BigDecimal sentimentScore;

    @Column(name = "av_overall_sentiment_label")
    private String sentimentLabel;

    @Column(name = "ingestion_time")
    private Timestamp ingestionTime;

    public CompanyNews() {
    }

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

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public String getUrlHash() {
        return urlHash;
    }

    public void setUrlHash(String urlHash) {
        this.urlHash = urlHash;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public Timestamp getPublishedAt() {
        return publishedAt;
    }

    public void setPublishedAt(Timestamp publishedAt) {
        this.publishedAt = publishedAt;
    }

    public BigDecimal getSentimentScore() {
        return sentimentScore;
    }

    public void setSentimentScore(BigDecimal sentimentScore) {
        this.sentimentScore = sentimentScore;
    }

    public String getSentimentLabel() {
        return sentimentLabel;
    }

    public void setSentimentLabel(String sentimentLabel) {
        this.sentimentLabel = sentimentLabel;
    }

    /**
     * Map the upstream 5-level label (Bullish, Somewhat-Bullish, Neutral,
     * Somewhat-Bearish, Bearish) to a simple 3-state for display badges.
     * Returns null when no sentiment data is available.
     */
    public String getSentimentTone() {
        if (sentimentLabel == null || sentimentLabel.isEmpty()) {
            return null;
        }
        String lower = sentimentLabel.toLowerCase();
        if (lower.contains("bullish")) {
            return "Positive";
        } else if (lower.contains("bearish")) {
            return "Negative";
        }
        return "Neutral";
    }

    public Timestamp getIngestionTime() {
        return ingestionTime;
    }

    public void setIngestionTime(Timestamp ingestionTime) {
        this.ingestionTime = ingestionTime;
    }
}
