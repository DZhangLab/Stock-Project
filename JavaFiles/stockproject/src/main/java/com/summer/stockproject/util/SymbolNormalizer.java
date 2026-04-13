package com.summer.stockproject.util;

/**
 * Single source of truth for stock-symbol normalization on the Java side.
 *
 * Two distinct outputs are produced from a raw URL/path symbol:
 *   - displaySymbol: the user-facing label (preserves dots, e.g. "BRK.B")
 *   - tableName:     the per-symbol intraday MySQL table identifier
 *                    (strips dots and rewrites MySQL reserved words)
 *
 * The rules mirror python_ingestion/symbols.py:normalize_table_name with
 * one Java-only addition: FB is rewritten to META (Facebook rebrand), which
 * also updates the display symbol so the UI shows the current ticker.
 */
public final class SymbolNormalizer {

    private SymbolNormalizer() {
    }

    /**
     * Normalize a raw symbol (typically from a URL path variable) into a
     * display/table pair. Preserves the exact branch order used historically
     * by StockController and IntradayBarServiceImpl.
     */
    public static NormalizedSymbol normalize(String rawSymbol) {
        if (rawSymbol == null) {
            throw new IllegalArgumentException("symbol must not be null");
        }
        String displaySymbol = rawSymbol.toUpperCase();
        String tableName = displaySymbol.replace(".", "").replace("/", "");

        switch (tableName) {
            case "NOW":
                tableName = "NOW1";
                break;
            case "ALL":
                tableName = "ALL1";
                break;
            case "KEYS":
                tableName = "KEYS1";
                break;
            case "KEY":
                tableName = "KEY1";
                break;
            case "FB":
                tableName = "META";
                displaySymbol = "META";
                break;
            default:
                break;
        }

        return new NormalizedSymbol(displaySymbol, tableName);
    }

    /**
     * Validate and normalize an already-derived table name for use in a
     * dynamic native query. Rejects anything outside [A-Z0-9] to prevent
     * SQL injection via the path variable. Rewrites FB → META defensively
     * in case a caller passes the raw (un-normalized) symbol.
     */
    public static String normalizeTableName(String tableName) {
        if (tableName == null || !tableName.matches("^[A-Z0-9]+$")) {
            throw new IllegalArgumentException("Invalid table name: " + tableName);
        }
        if (tableName.equals("FB")) {
            return "META";
        }
        return tableName;
    }

    /** Value object holding the display label and the table identifier. */
    public static final class NormalizedSymbol {
        public final String displaySymbol;
        public final String tableName;

        public NormalizedSymbol(String displaySymbol, String tableName) {
            this.displaySymbol = displaySymbol;
            this.tableName = tableName;
        }
    }
}
