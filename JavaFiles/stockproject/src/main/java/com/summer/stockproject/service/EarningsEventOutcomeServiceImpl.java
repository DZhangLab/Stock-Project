package com.summer.stockproject.service;

import com.summer.stockproject.dao.EarningsEventOutcomeRepository;
import com.summer.stockproject.dao.EarningsToneIndexProjection;
import com.summer.stockproject.entity.EarningsEventOutcome;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

@Service
public class EarningsEventOutcomeServiceImpl implements EarningsEventOutcomeService {

    private static final long BOOTSTRAP_SEED = 20260510L;
    private static final int SMALL_SAMPLE_WARNING_N = 30;

    private final EarningsEventOutcomeRepository repository;

    @Autowired
    public EarningsEventOutcomeServiceImpl(EarningsEventOutcomeRepository repository) {
        this.repository = repository;
    }

    @Override
    public List<EarningsEventOutcome> getBySymbol(String symbol) {
        String normalizedSymbol = normalizeSymbol(symbol);
        if (normalizedSymbol.isEmpty()) {
            return Collections.emptyList();
        }
        List<EarningsEventOutcome> rows = repository.findBySymbolOrderByEventDateDesc(normalizedSymbol);
        if (rows == null || rows.isEmpty()) {
            return Collections.emptyList();
        }
        attachToneIndexes(normalizedSymbol, rows);
        return rows;
    }

    @Override
    public EarningsEventOutcome getBySymbolAndPeriod(String symbol, String period) {
        String normalizedSymbol = normalizeSymbol(symbol);
        String normalizedPeriod = normalizePeriod(period);
        if (normalizedSymbol.isEmpty() || normalizedPeriod.isEmpty()) {
            return null;
        }
        EarningsEventOutcome row = repository.findTopBySymbolAndNormalizedFiscalPeriodLabelOrderByEventDateDesc(
                normalizedSymbol,
                normalizedPeriod
        );
        if (row != null) {
            attachToneIndexes(normalizedSymbol, Collections.singletonList(row));
        }
        return row;
    }

    @Override
    public Map<String, Object> getAggregateAnalysis(
            String bucket,
            String window,
            String symbol,
            String symbols,
            String quality,
            int minBucketSize,
            int bootstrapSamples
    ) {
        String normalizedBucket = normalizeBucket(bucket);
        String normalizedWindow = normalizeWindow(window);
        String normalizedQuality = normalizeQuality(quality);
        int effectiveMinBucketSize = Math.max(1, minBucketSize);
        int effectiveBootstrapSamples = Math.max(1, bootstrapSamples);
        Set<String> symbolFilter = buildSymbolFilter(symbol, symbols);

        List<EarningsEventOutcome> rows = repository.findAll();
        Map<String, List<Double>> bucketValues = initializeBuckets(normalizedBucket, normalizedQuality);
        int totalEvents = 0;
        int usableEvents = 0;

        for (EarningsEventOutcome row : rows) {
            if (row == null || !matchesSymbolFilter(row, symbolFilter) || !matchesQuality(row, normalizedQuality)) {
                continue;
            }
            totalEvents++;

            BigDecimal selectedReturn = selectedReturn(row, normalizedWindow);
            if (selectedReturn == null) {
                continue;
            }

            String bucketName = bucketName(row, normalizedBucket, normalizedQuality);
            if (bucketName == null) {
                continue;
            }

            if (!bucketValues.containsKey(bucketName)) {
                bucketValues.put(bucketName, new ArrayList<Double>());
            }
            bucketValues.get(bucketName).add(selectedReturn.doubleValue());
            usableEvents++;
        }

        List<Map<String, Object>> bucketResults = new ArrayList<Map<String, Object>>();
        for (Map.Entry<String, List<Double>> entry : bucketValues.entrySet()) {
            if (entry.getValue().isEmpty()) {
                continue;
            }
            bucketResults.add(buildBucketResult(
                    entry.getKey(),
                    entry.getValue(),
                    normalizedBucket,
                    normalizedWindow,
                    effectiveMinBucketSize,
                    effectiveBootstrapSamples
            ));
        }

        Map<String, Object> response = new LinkedHashMap<String, Object>();
        response.put("bucket", normalizedBucket);
        response.put("window", normalizedWindow);
        response.put("quality", normalizedQuality);
        response.put("symbolFilter", new ArrayList<String>(symbolFilter));
        response.put("totalEvents", totalEvents);
        response.put("usableEvents", usableEvents);
        response.put("minBucketSize", effectiveMinBucketSize);
        response.put("bootstrapSamples", effectiveBootstrapSamples);
        response.put("warning", buildWarning(usableEvents));
        response.put("buckets", bucketResults);
        return response;
    }

    private String normalizeSymbol(String symbol) {
        return symbol == null ? "" : symbol.trim().toUpperCase();
    }

    private void attachToneIndexes(String symbol, List<EarningsEventOutcome> rows) {
        List<EarningsToneIndexProjection> toneRows = repository.findToneIndexesBySymbol(symbol);
        if (toneRows == null || toneRows.isEmpty()) {
            return;
        }

        Map<String, BigDecimal> toneIndexByPeriod = new LinkedHashMap<String, BigDecimal>();
        for (EarningsToneIndexProjection toneRow : toneRows) {
            if (toneRow == null) {
                continue;
            }
            String period = normalizePeriod(toneRow.getNormalizedFiscalPeriodLabel());
            if (!period.isEmpty()) {
                toneIndexByPeriod.put(period, toneRow.getAiToneIndex());
            }
        }

        for (EarningsEventOutcome row : rows) {
            if (row == null) {
                continue;
            }
            String period = normalizePeriod(row.getNormalizedFiscalPeriodLabel());
            row.setAiToneIndex(toneIndexByPeriod.get(period));
        }
    }

    private String normalizePeriod(String period) {
        if (period == null) {
            return "";
        }
        String normalized = period.trim().toUpperCase();
        if (normalized.startsWith("FY")) {
            normalized = normalized.substring(2);
        }
        return normalized;
    }

    private String normalizeBucket(String bucket) {
        String normalized = bucket == null ? "tone" : bucket.trim().toLowerCase();
        if ("tone".equals(normalized) || "surprise".equals(normalized) || "quality".equals(normalized)) {
            return normalized;
        }
        throw new IllegalArgumentException("Unsupported bucket. Use tone, surprise, or quality.");
    }

    private String normalizeWindow(String window) {
        String normalized = window == null ? "5d" : window.trim().toLowerCase();
        if ("1d".equals(normalized) || "3d".equals(normalized) || "5d".equals(normalized) || "20d".equals(normalized)) {
            return normalized;
        }
        throw new IllegalArgumentException("Unsupported window. Use 1d, 3d, 5d, or 20d.");
    }

    private String normalizeQuality(String quality) {
        String normalized = quality == null ? "" : quality.trim().toLowerCase();
        if (normalized.isEmpty() || "non_excluded".equals(normalized) || "non-excluded".equals(normalized)) {
            return "non_excluded";
        }
        if ("full".equals(normalized) || "partial".equals(normalized) || "all".equals(normalized)) {
            return normalized;
        }
        throw new IllegalArgumentException("Unsupported quality. Use full, partial, non_excluded, or all.");
    }

    private Set<String> buildSymbolFilter(String symbol, String symbols) {
        Set<String> filters = new LinkedHashSet<String>();
        String normalizedSymbol = normalizeSymbol(symbol);
        if (!normalizedSymbol.isEmpty()) {
            filters.add(normalizedSymbol);
        }
        if (symbols != null) {
            List<String> parts = Arrays.asList(symbols.split(","));
            for (String part : parts) {
                String normalized = normalizeSymbol(part);
                if (!normalized.isEmpty()) {
                    filters.add(normalized);
                }
            }
        }
        return filters;
    }

    private boolean matchesSymbolFilter(EarningsEventOutcome row, Set<String> symbolFilter) {
        if (symbolFilter.isEmpty()) {
            return true;
        }
        return symbolFilter.contains(normalizeSymbol(row.getSymbol()));
    }

    private boolean matchesQuality(EarningsEventOutcome row, String quality) {
        String flag = normalizeQualityFlag(row.getQualityFlag());
        if ("all".equals(quality)) {
            return true;
        }
        if ("full".equals(quality)) {
            return "full".equals(flag);
        }
        if ("partial".equals(quality)) {
            return "full".equals(flag) || "partial".equals(flag);
        }
        return !"excluded".equals(flag);
    }

    private String normalizeQualityFlag(String qualityFlag) {
        String flag = qualityFlag == null ? "" : qualityFlag.trim().toLowerCase();
        return flag.isEmpty() ? "partial" : flag;
    }

    private BigDecimal selectedReturn(EarningsEventOutcome row, String window) {
        if ("1d".equals(window)) {
            return row.getRet1d();
        }
        if ("3d".equals(window)) {
            return row.getRet3d();
        }
        if ("20d".equals(window)) {
            return row.getRet20d();
        }
        return row.getRet5d();
    }

    private Map<String, List<Double>> initializeBuckets(String bucket, String quality) {
        Map<String, List<Double>> buckets = new LinkedHashMap<String, List<Double>>();
        if ("surprise".equals(bucket)) {
            buckets.put("negative surprise", new ArrayList<Double>());
            buckets.put("small positive surprise", new ArrayList<Double>());
            buckets.put("large positive surprise", new ArrayList<Double>());
        } else if ("quality".equals(bucket)) {
            buckets.put("full", new ArrayList<Double>());
            buckets.put("partial", new ArrayList<Double>());
            if ("all".equals(quality)) {
                buckets.put("excluded", new ArrayList<Double>());
            }
        }
        return buckets;
    }

    private String bucketName(EarningsEventOutcome row, String bucket, String quality) {
        if ("tone".equals(bucket)) {
            String tone = row.getAiOverallToneAtEvent();
            if (tone == null || tone.trim().isEmpty()) {
                return "all".equals(quality) ? "missing" : null;
            }
            return tone.trim().toLowerCase();
        }
        if ("surprise".equals(bucket)) {
            BigDecimal surprise = row.getSurprisePctAtEvent();
            if (surprise == null) {
                return null;
            }
            double surpriseValue = surprise.doubleValue();
            if (surpriseValue < 0.0d) {
                return "negative surprise";
            }
            if (surpriseValue < 5.0d) {
                return "small positive surprise";
            }
            return "large positive surprise";
        }
        if ("quality".equals(bucket)) {
            return normalizeQualityFlag(row.getQualityFlag());
        }
        return null;
    }

    private Map<String, Object> buildBucketResult(
            String bucketName,
            List<Double> values,
            String bucketType,
            String window,
            int minBucketSize,
            int bootstrapSamples
    ) {
        Map<String, Object> result = new LinkedHashMap<String, Object>();
        int n = values.size();
        result.put("bucketName", bucketName);
        result.put("n", n);
        result.put("meanReturn", mean(values));
        result.put("medianReturn", median(values));
        result.put("window", window);
        result.put("bucketType", bucketType);
        if (n < minBucketSize) {
            result.put("ciLow", null);
            result.put("ciHigh", null);
            result.put("note", "Bucket n is below minBucketSize; bootstrap CI omitted.");
        } else {
            double[] ci = bootstrapMeanCi(values, bootstrapSamples, BOOTSTRAP_SEED + bucketName.hashCode());
            result.put("ciLow", ci[0]);
            result.put("ciHigh", ci[1]);
        }
        return result;
    }

    private double mean(List<Double> values) {
        double total = 0.0d;
        for (Double value : values) {
            total += value;
        }
        return total / values.size();
    }

    private double median(List<Double> values) {
        List<Double> sorted = new ArrayList<Double>(values);
        Collections.sort(sorted);
        int size = sorted.size();
        if (size % 2 == 1) {
            return sorted.get(size / 2);
        }
        return (sorted.get((size / 2) - 1) + sorted.get(size / 2)) / 2.0d;
    }

    private double[] bootstrapMeanCi(List<Double> values, int samples, long seed) {
        Random random = new Random(seed);
        List<Double> means = new ArrayList<Double>(samples);
        int n = values.size();
        for (int sample = 0; sample < samples; sample++) {
            double total = 0.0d;
            for (int i = 0; i < n; i++) {
                total += values.get(random.nextInt(n));
            }
            means.add(total / n);
        }
        means.sort(Comparator.naturalOrder());
        int lowIndex = percentileIndex(samples, 0.025d);
        int highIndex = percentileIndex(samples, 0.975d);
        return new double[] { means.get(lowIndex), means.get(highIndex) };
    }

    private int percentileIndex(int size, double percentile) {
        int index = (int) Math.floor(percentile * (size - 1));
        return Math.max(0, Math.min(size - 1, index));
    }

    private String buildWarning(int usableEvents) {
        if (usableEvents == 0) {
            return "No usable events for this selection; descriptive only.";
        }
        if (usableEvents < SMALL_SAMPLE_WARNING_N) {
            return "Small sample size; descriptive only. This is not a prediction or trading signal.";
        }
        return "Descriptive only. This is not a prediction or trading signal.";
    }
}
