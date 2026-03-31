package com.summer.stockproject.controller;

import com.summer.stockproject.entity.CompanyNewsAiSummary;
import com.summer.stockproject.entity.EarningsAiAnalysis;
import com.summer.stockproject.entity.EarningsCallSummary;
import com.summer.stockproject.entity.QuarterlyReportingSnapshot;
import com.summer.stockproject.service.CompanyNewsAiSummaryService;
import com.summer.stockproject.service.EarningsAiAnalysisService;
import com.summer.stockproject.service.EarningsCallSummaryService;
import com.summer.stockproject.service.QuarterlyReportingSnapshotService;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/financials")
public class FinancialsController {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private final QuarterlyReportingSnapshotService quarterlyReportingSnapshotService;
    private final EarningsCallSummaryService earningsCallSummaryService;
    private final CompanyNewsAiSummaryService companyNewsAiSummaryService;
    private final EarningsAiAnalysisService earningsAiAnalysisService;

    @Autowired
    public FinancialsController(
            QuarterlyReportingSnapshotService quarterlyReportingSnapshotService,
            EarningsCallSummaryService earningsCallSummaryService,
            CompanyNewsAiSummaryService companyNewsAiSummaryService,
            EarningsAiAnalysisService earningsAiAnalysisService
    ) {
        this.quarterlyReportingSnapshotService = quarterlyReportingSnapshotService;
        this.earningsCallSummaryService = earningsCallSummaryService;
        this.companyNewsAiSummaryService = companyNewsAiSummaryService;
        this.earningsAiAnalysisService = earningsAiAnalysisService;
    }

    @GetMapping("/quarterly/latest")
    public ResponseEntity<Map<String, Object>> getLatestQuarterlySnapshot(
            @RequestParam(defaultValue = "AAPL") String symbol
    ) {
        QuarterlyReportingSnapshot snapshot = quarterlyReportingSnapshotService.getLatestBySymbol(symbol);
        if (snapshot == null) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
            notFound.put("message", "No quarterly snapshot found");
            return ResponseEntity.status(404).body(notFound);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", snapshot.getSymbol());
        response.put("fiscalDateEnding", snapshot.getFiscalDateEnding() == null ? null : snapshot.getFiscalDateEnding().toString());
        response.put("fiscalPeriodLabel", snapshot.getFiscalPeriodLabel());
        response.put("reportedDate", snapshot.getReportedDate() == null ? null : snapshot.getReportedDate().toString());
        response.put("reportedCurrency", snapshot.getReportedCurrency());
        response.put("totalRevenue", snapshot.getTotalRevenue());
        response.put("netIncome", snapshot.getNetIncome());
        response.put("reportedEps", snapshot.getReportedEps());
        response.put("estimatedEps", snapshot.getEstimatedEps());
        response.put("surprise", snapshot.getSurprise());
        response.put("surprisePercentage", snapshot.getSurprisePercentage());
        response.put("updatedAt", snapshot.getUpdatedAt() == null ? null : snapshot.getUpdatedAt().toString());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/earnings/latest")
    public ResponseEntity<Map<String, Object>> getLatestEarningsCallSummary(
            @RequestParam(defaultValue = "AAPL") String symbol
    ) {
        EarningsCallSummary summary = earningsCallSummaryService.getLatestBySymbol(symbol);
        if (summary == null) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
            notFound.put("message", "No earnings call summary found");
            return ResponseEntity.status(404).body(notFound);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", summary.getSymbol());
        response.put("fiscalPeriodLabelRaw", summary.getFiscalPeriodLabel());
        response.put("fiscalPeriodLabel", normalizeFiscalPeriodLabel(summary.getFiscalPeriodLabel()));
        response.put("callDate", summary.getCallDate() == null ? null : summary.getCallDate().toString());
        response.put("source", summary.getSource());
        response.put("summaryText", summary.getSummaryText());
        response.put("keyTakeawaysJson", summary.getKeyTakeawaysJson());
        Map<String, List<String>> sections = parseTakeawaySections(summary.getKeyTakeawaysJson());
        response.put("keyHighlights", sections.get("keyHighlights"));
        response.put("mainRisksConcerns", sections.get("mainRisksConcerns"));
        response.put("outlookGuidance", sections.get("outlookGuidance"));
        response.put("transcriptUrl", summary.getTranscriptUrl());
        response.put("updatedAt", summary.getUpdatedAt() == null ? null : summary.getUpdatedAt().toString());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/news-ai/latest")
    public ResponseEntity<Map<String, Object>> getLatestCompanyNewsAiSummary(
            @RequestParam(defaultValue = "AAPL") String symbol
    ) {
        CompanyNewsAiSummary summary = companyNewsAiSummaryService.getLatestBySymbol(symbol);
        if (summary == null) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
            notFound.put("message", "No AI news summary found");
            return ResponseEntity.status(404).body(notFound);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", summary.getSymbol());
        response.put("analysisDate", summary.getAnalysisDate() == null ? null : summary.getAnalysisDate().toString());
        response.put("sourceWindowLabel", summary.getSourceWindowLabel());
        response.put("sourceNewsCount", summary.getSourceNewsCount());
        response.put("overallSentimentLabel", summary.getOverallSentimentLabel());
        response.put("overallSentimentSummary", summary.getOverallSentimentSummary());
        response.put("mainThemes", parseStringArray(summary.getMainThemesJson()));
        response.put("topPositiveDriver", summary.getTopPositiveDriver());
        response.put("topRiskConcern", summary.getTopRiskConcern());
        response.put("confidenceNote", summary.getConfidenceNote());
        response.put("provider", summary.getProvider());
        response.put("modelName", summary.getModelName());
        response.put("promptVersion", summary.getPromptVersion());
        response.put("updatedAt", summary.getUpdatedAt() == null ? null : summary.getUpdatedAt().toString());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/earnings-ai/latest")
    public ResponseEntity<Map<String, Object>> getLatestEarningsAiAnalysis(
            @RequestParam(defaultValue = "AAPL") String symbol
    ) {
        EarningsAiAnalysis analysis = earningsAiAnalysisService.getLatestBySymbol(symbol);
        if (analysis == null) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
            notFound.put("message", "No earnings AI analysis found");
            return ResponseEntity.status(404).body(notFound);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", analysis.getSymbol());
        response.put("fiscalPeriodLabelRaw", analysis.getFiscalPeriodLabel());
        response.put("fiscalPeriodLabel", normalizeFiscalPeriodLabel(analysis.getFiscalPeriodLabel()));
        response.put("callDate", analysis.getCallDate() == null ? null : analysis.getCallDate().toString());
        response.put("source", analysis.getSource());
        response.put("transcriptUrl", analysis.getTranscriptUrl());
        response.put("transcriptCharCount", analysis.getTranscriptCharCount());
        response.put("transcriptSegmentCount", analysis.getTranscriptSegmentCount());
        response.put("toneAnalyzer", analysis.getToneAnalyzer());
        response.put("overallTone", analysis.getOverallTone());
        response.put("keyHighlights", parseStringArray(analysis.getKeyHighlightsJson()));
        response.put("mainRisksConcerns", parseStringArray(analysis.getMainRisksConcernsJson()));
        response.put("outlookGuidance", parseStringArray(analysis.getOutlookGuidanceJson()));
        response.put("provider", analysis.getProvider());
        response.put("modelName", analysis.getModelName());
        response.put("promptVersion", analysis.getPromptVersion());
        response.put("updatedAt", analysis.getUpdatedAt() == null ? null : analysis.getUpdatedAt().toString());
        return ResponseEntity.ok(response);
    }

    private String normalizeFiscalPeriodLabel(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim().toUpperCase();
        if (normalized.matches("^\\d{4}Q[1-4]$")) {
            return "FY" + normalized;
        }
        return normalized;
    }

    private static void addIfRoom(List<String> target, String value, int maxSize) {
        if (value == null) {
            return;
        }
        String text = value.trim();
        if (text.isEmpty()) {
            return;
        }
        if (target.size() >= maxSize || target.contains(text)) {
            return;
        }
        target.add(text);
    }

    private static String stripPrefix(String value, String prefix) {
        if (value == null) {
            return "";
        }
        String text = value.trim();
        if (text.toLowerCase().startsWith(prefix.toLowerCase() + ":")) {
            return text.substring(prefix.length() + 1).trim();
        }
        return text;
    }

    private static boolean containsAny(String text, String[] keywords) {
        String lower = text.toLowerCase();
        for (String keyword : keywords) {
            if (lower.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    private static boolean isPerformanceHighlightText(String text) {
        String[] positiveKeywords = {
                "record",
                "all-time high",
                "growth",
                "up ",
                "improved",
                "increasing",
                "favorable mix",
                "strong demand"
        };
        if (containsAny(text, positiveKeywords)) {
            return true;
        }
        // Special-case margin commentary: classify as highlight if the sentence is mostly positive.
        return text.toLowerCase().contains("gross margin")
                && (text.toLowerCase().contains("increasing") || text.toLowerCase().contains("favorable mix"));
    }

    private static boolean isRiskConcernText(String text) {
        String[] riskKeywords = {
                "supply constraint",
                "constraints",
                "softness",
                "flat",
                "decline",
                "down",
                "pressure",
                "tough comparison",
                "tough comparisons",
                "headwind",
                "challenging"
        };
        return containsAny(text, riskKeywords);
    }

    private List<String> parseStringArray(String rawJson) {
        if (rawJson == null || rawJson.trim().isEmpty()) {
            return Collections.emptyList();
        }
        try {
            List<String> items = OBJECT_MAPPER.readValue(rawJson, new TypeReference<List<String>>() {});
            List<String> cleaned = new ArrayList<>();
            for (String item : items) {
                if (item == null) {
                    continue;
                }
                String text = item.trim();
                if (!text.isEmpty() && !cleaned.contains(text)) {
                    cleaned.add(text);
                }
            }
            return cleaned;
        } catch (java.io.IOException ignored) {
            return Collections.emptyList();
        }
    }

    private Map<String, List<String>> parseTakeawaySections(String rawJson) {
        List<String> highlights = new ArrayList<>();
        List<String> risks = new ArrayList<>();
        List<String> outlook = new ArrayList<>();

        if (rawJson != null && !rawJson.trim().isEmpty()) {
            try {
                List<String> items = OBJECT_MAPPER.readValue(rawJson, new TypeReference<List<String>>() {});
                for (String item : items) {
                    if (item == null) {
                        continue;
                    }
                    String text = item.trim();
                    if (text.isEmpty()) {
                        continue;
                    }
                    if (text.toLowerCase().startsWith("key highlights:")) {
                        addIfRoom(highlights, stripPrefix(text, "Key Highlights"), 2);
                    } else if (text.toLowerCase().startsWith("main risks / concerns:")) {
                        String cleaned = stripPrefix(text, "Main Risks / Concerns");
                        // Priority rule: strong performance language should stay in Highlights
                        // even if the sentence also contains a generic risk keyword.
                        if (isPerformanceHighlightText(cleaned)) {
                            // Keep reclassified performance commentary instead of dropping it
                            // when the original highlight slots are already filled.
                            addIfRoom(highlights, cleaned, 3);
                        } else if (isRiskConcernText(cleaned)) {
                            addIfRoom(risks, cleaned, 2);
                        } else {
                            addIfRoom(risks, cleaned, 2);
                        }
                    } else if (text.toLowerCase().startsWith("outlook / guidance:")) {
                        addIfRoom(outlook, stripPrefix(text, "Outlook / Guidance"), 2);
                    } else {
                        addIfRoom(highlights, text, 2);
                    }
                }
            } catch (java.io.IOException ignored) {
                // Keep section lists empty when JSON parsing fails.
            }
        }

        Map<String, List<String>> sections = new LinkedHashMap<>();
        sections.put("keyHighlights", highlights.isEmpty() ? Collections.emptyList() : highlights);
        sections.put("mainRisksConcerns", risks.isEmpty() ? Collections.emptyList() : risks);
        sections.put("outlookGuidance", outlook.isEmpty() ? Collections.emptyList() : outlook);
        return sections;
    }
}
