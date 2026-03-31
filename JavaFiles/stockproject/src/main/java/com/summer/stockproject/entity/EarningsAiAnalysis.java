package com.summer.stockproject.entity;

import javax.persistence.*;
import java.sql.Date;
import java.sql.Timestamp;

@Entity
@Table(name = "earnings_ai_analysis")
public class EarningsAiAnalysis {

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

    @Column(name = "transcript_url")
    private String transcriptUrl;

    @Column(name = "transcript_char_count")
    private Integer transcriptCharCount;

    @Column(name = "transcript_segment_count")
    private Integer transcriptSegmentCount;

    @Column(name = "tone_analyzer")
    private String toneAnalyzer;

    @Column(name = "tone_summary_json")
    private String toneSummaryJson;

    @Column(name = "overall_tone")
    private String overallTone;

    @Column(name = "key_highlights_json")
    private String keyHighlightsJson;

    @Column(name = "main_risks_concerns_json")
    private String mainRisksConcernsJson;

    @Column(name = "outlook_guidance_json")
    private String outlookGuidanceJson;

    @Column(name = "provider")
    private String provider;

    @Column(name = "model_name")
    private String modelName;

    @Column(name = "prompt_version")
    private String promptVersion;

    @Column(name = "raw_model_response_json")
    private String rawModelResponseJson;

    @Column(name = "raw_transcript_payload_json")
    private String rawTranscriptPayloadJson;

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

    public String getTranscriptUrl() {
        return transcriptUrl;
    }

    public void setTranscriptUrl(String transcriptUrl) {
        this.transcriptUrl = transcriptUrl;
    }

    public Integer getTranscriptCharCount() {
        return transcriptCharCount;
    }

    public void setTranscriptCharCount(Integer transcriptCharCount) {
        this.transcriptCharCount = transcriptCharCount;
    }

    public Integer getTranscriptSegmentCount() {
        return transcriptSegmentCount;
    }

    public void setTranscriptSegmentCount(Integer transcriptSegmentCount) {
        this.transcriptSegmentCount = transcriptSegmentCount;
    }

    public String getToneAnalyzer() {
        return toneAnalyzer;
    }

    public void setToneAnalyzer(String toneAnalyzer) {
        this.toneAnalyzer = toneAnalyzer;
    }

    public String getToneSummaryJson() {
        return toneSummaryJson;
    }

    public void setToneSummaryJson(String toneSummaryJson) {
        this.toneSummaryJson = toneSummaryJson;
    }

    public String getOverallTone() {
        return overallTone;
    }

    public void setOverallTone(String overallTone) {
        this.overallTone = overallTone;
    }

    public String getKeyHighlightsJson() {
        return keyHighlightsJson;
    }

    public void setKeyHighlightsJson(String keyHighlightsJson) {
        this.keyHighlightsJson = keyHighlightsJson;
    }

    public String getMainRisksConcernsJson() {
        return mainRisksConcernsJson;
    }

    public void setMainRisksConcernsJson(String mainRisksConcernsJson) {
        this.mainRisksConcernsJson = mainRisksConcernsJson;
    }

    public String getOutlookGuidanceJson() {
        return outlookGuidanceJson;
    }

    public void setOutlookGuidanceJson(String outlookGuidanceJson) {
        this.outlookGuidanceJson = outlookGuidanceJson;
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

    public String getRawModelResponseJson() {
        return rawModelResponseJson;
    }

    public void setRawModelResponseJson(String rawModelResponseJson) {
        this.rawModelResponseJson = rawModelResponseJson;
    }

    public String getRawTranscriptPayloadJson() {
        return rawTranscriptPayloadJson;
    }

    public void setRawTranscriptPayloadJson(String rawTranscriptPayloadJson) {
        this.rawTranscriptPayloadJson = rawTranscriptPayloadJson;
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
