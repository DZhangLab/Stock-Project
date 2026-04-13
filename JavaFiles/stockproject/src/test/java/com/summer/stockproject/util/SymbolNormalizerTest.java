package com.summer.stockproject.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SymbolNormalizerTest {

    @Test
    void plainSymbolUppercased() {
        SymbolNormalizer.NormalizedSymbol n = SymbolNormalizer.normalize("aapl");
        assertEquals("AAPL", n.displaySymbol);
        assertEquals("AAPL", n.tableName);
    }

    @Test
    void dotPreservedInDisplayStrippedInTable() {
        SymbolNormalizer.NormalizedSymbol brkb = SymbolNormalizer.normalize("BRK.B");
        assertEquals("BRK.B", brkb.displaySymbol);
        assertEquals("BRKB", brkb.tableName);

        SymbolNormalizer.NormalizedSymbol bfb = SymbolNormalizer.normalize("BF.B");
        assertEquals("BF.B", bfb.displaySymbol);
        assertEquals("BFB", bfb.tableName);
    }

    @Test
    void reservedWordNowSuffixed() {
        SymbolNormalizer.NormalizedSymbol n = SymbolNormalizer.normalize("NOW");
        assertEquals("NOW", n.displaySymbol);
        assertEquals("NOW1", n.tableName);
    }

    @Test
    void reservedWordAllSuffixed() {
        SymbolNormalizer.NormalizedSymbol n = SymbolNormalizer.normalize("ALL");
        assertEquals("ALL", n.displaySymbol);
        assertEquals("ALL1", n.tableName);
    }

    @Test
    void reservedWordKeysSuffixed() {
        SymbolNormalizer.NormalizedSymbol n = SymbolNormalizer.normalize("KEYS");
        assertEquals("KEYS", n.displaySymbol);
        assertEquals("KEYS1", n.tableName);
    }

    @Test
    void reservedWordKeySuffixed() {
        SymbolNormalizer.NormalizedSymbol n = SymbolNormalizer.normalize("KEY");
        assertEquals("KEY", n.displaySymbol);
        assertEquals("KEY1", n.tableName);
    }

    @Test
    void fbRewrittenToMetaForBothFields() {
        SymbolNormalizer.NormalizedSymbol n = SymbolNormalizer.normalize("FB");
        assertEquals("META", n.displaySymbol);
        assertEquals("META", n.tableName);
    }

    @Test
    void nowxIsNotMangled() {
        // Only exact "NOW" collides with the MySQL reserved word.
        SymbolNormalizer.NormalizedSymbol n = SymbolNormalizer.normalize("NOWX");
        assertEquals("NOWX", n.displaySymbol);
        assertEquals("NOWX", n.tableName);
    }

    @Test
    void normalizeTableNameAcceptsClean() {
        assertEquals("AAPL", SymbolNormalizer.normalizeTableName("AAPL"));
    }

    @Test
    void normalizeTableNameRewritesFb() {
        assertEquals("META", SymbolNormalizer.normalizeTableName("FB"));
    }

    @Test
    void normalizeTableNameRejectsInvalid() {
        assertThrows(IllegalArgumentException.class,
                () -> SymbolNormalizer.normalizeTableName("brk.b"));
        assertThrows(IllegalArgumentException.class,
                () -> SymbolNormalizer.normalizeTableName(null));
        assertThrows(IllegalArgumentException.class,
                () -> SymbolNormalizer.normalizeTableName("AA; DROP TABLE"));
    }
}
