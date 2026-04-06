"""
Symbol management module for maintaining stock symbol lists.
"""
from typing import List


# Stock symbol list matching the JavaScript version
SYMBOL_LIST: List[str] = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "TSLA", "BRK.B", "JNJ", "UNH", "META",
    "NVDA", "XOM", "JPM", "PG", "V", "CVX", "HD", "MA", "PFE", "ABBV",
    "BAC", "KO", "MRK", "LLY", "AVGO", "PEP", "TMO", "VZ", "ABT", "CMCSA",
    "DIS", "COST", "ADBE", "CSCO", "ACN", "MCD", "INTC", "WMT", "BMY", "WFC",
    "LIN", "DHR", "AMD", "PM", "TXN", "CRM", "QCOM", "T", "NEE", "MDT",
    "UNP", "AMGN", "COP", "NKE", "RTX", "HON", "LOW", "CVS", "UPS", "SPGI",
    "IBM", "ANTM", "MS", "CAT", "AMT", "ORCL", "GS", "LMT", "INTU", "DE",
    "C", "AMAT", "AXP", "PYPL", "SCHW", "MO", "PLD", "CB", "ADP", "BKNG",
    "NOW", "MDLZ", "ADI", "BLK", "MMM", "DUK", "GE", "CI", "SBUX", "NFLX",
    "GILD", "ISRG", "SO", "MU", "SYK", "CCI", "MMC", "ZTS", "TMUS", "TGT",
    "TJX", "BDX", "EOG", "REGN", "BA", "CSX", "CME", "D", "USB", "LRCX",
    "NOC", "PNC", "VRTX", "PGR", "CL", "SHW", "TFC", "ATVI", "PXD", "FIS",
    "EW", "WM", "ITW", "SLB", "AON", "EQIX", "CHTR", "OXY", "FISV", "BSX",
    "MPC", "HUM", "EL", "NSC", "ETN", "ICE", "FCX", "NEM", "GM", "SRE",
    "APD", "KLAC", "DOW", "VLO", "F", "MRNA", "GD", "AEP", "EMR", "HCA",
    "FDX", "CNC", "AIG", "MCK", "PSA", "COF", "DG", "NXPI", "ADM", "EXC",
    "SNPS", "MCO", "LHX", "PSX", "MET", "DVN", "ROP", "KMB", "CTVA", "MAR",
    "ADSK", "WMB", "TRV", "ORLY", "SYY", "APH", "XEL", "TEL", "GIS", "CDNS",
    "ECL", "AZO", "HPQ", "WBD", "IQV", "STZ", "WELL", "O", "ILMN", "PRU",
    "FTNT", "PAYX", "KMI", "A", "CTSH", "EA", "HLT", "MCHP", "JCI", "DLR",
    "BAX", "SPG", "CMG", "MSI", "ALL", "SBAC", "GPN", "PEG", "PH", "ED",
    "AFL", "MSCI", "DD", "ROST", "NUE", "IFF", "MNST", "HAL", "AJG", "WEC",
    "KR", "BK", "CARR", "YUM", "BKR", "CTAS", "HES", "IDXX", "OTIS", "ES",
    "TT", "DXCM", "DLTR", "DFS", "HSY", "TWTR", "FAST", "MTB", "WBA", "PPG",
    "RMD", "CMI", "LYB", "TDG", "BIIB", "WY", "AMP", "PCAR", "OKE", "MTD",
    "EBAY", "ALB", "AVB", "CERN", "TROW", "KHC", "VRSK", "AME", "CBRE", "RSG",
    "AWK", "FRC", "LUV", "APTV", "SIVB", "KEYS", "GLW", "DAL", "EIX", "EQR",
    "DTE", "TSN", "CTRA", "WTW", "ZBH", "FITB", "STT", "FE", "AEE", "CPRT",
    "EFX", "ETR", "ROK", "ARE", "LH", "BALL", "ANET", "EXR", "MOS", "HIG",
    "ABC", "STE", "VTR", "ODFL", "WST", "ENPH", "MKC", "PPL", "FANG", "CDW",
    "DHI", "CF", "ANSS", "CHD", "MTCH", "VMC", "NTRS", "MRO", "TSCO", "FTV",
    "IT", "GWW", "MLM", "ALGN", "CMS", "MAA", "WAT", "AMCR", "HOLX", "URI",
    "HPE", "DRE", "PARA", "CNP", "ULTA", "RF", "EXPE", "LEN", "HBAN", "GPC",
    "SWK", "CFG", "IP", "CEG", "DOV", "EPAM", "CINF", "FLT", "ESS", "TDY",
    "WDC", "MOH", "PKI", "MPWR", "IR", "CTLT", "EXPD", "J", "ZBRA", "K",
    "KEY", "SYF", "PFG", "RJF", "CLX", "DGX", "SWKS", "TER", "COO", "NDAQ",
    "STX", "WAB", "CE", "TRMB", "PWR", "AKAM", "BR", "BBY", "VRSN", "POOL",
    "PEAK", "OMC", "CAH", "FMC", "NTAP", "EVRG", "CAG", "GRMN", "ATO", "DRI",
    "BXP", "APA", "KMX", "XYL", "LNT", "VFC", "PKG", "CPT", "LDOS", "TECH",
    "UAL", "VTRS", "IRM", "GNRC", "INCY", "KIM", "WRB", "IEX", "TYL", "AVY",
    "TTWO", "UDR", "TXT", "HST", "NLOK", "AES", "SJM", "FDS", "NVR", "HRL",
    "JBHT", "LKQ", "TFX", "EMN", "CHRW", "SEDG", "JKHY", "MAS", "PAYC", "RCL",
    "HWM", "BRO", "MGM", "DPZ", "L", "CTXS", "LYV", "AAP", "IPG", "WRK",
    "SBNY", "NI", "CRL", "SNA", "PTC", "HSIC", "LVS", "QRVO", "NRG", "BF.B",
    "CBOE", "BIO", "NDSN", "HAS", "RE", "CCL", "AAL", "ABMD", "FOXA", "PHM",
    "BBWI", "LUMN", "CZR", "WHR", "AIZ", "MKTX", "ETSY", "RHI", "REG", "ALLE",
    "CMA", "TAP", "CPB", "JNPR", "BWA", "FFIV", "OGN", "NLSN", "FBHS", "LW",
    "SEE", "LNC", "GL", "UHS", "PNW", "TPR", "XRAY", "HII", "PNR", "ZION",
    "MHK", "FRT", "AOS", "ROL", "CDAY", "NWL", "DXC", "BEN", "NWSA", "NCLH",
    "WYNN", "IVZ", "ALK", "DVA", "VNO", "DISH", "PENN", "PVH", "FOX", "RL",
    "IPGP", "NWS", "UAA", "UA", "EMBC"
]


def load_symbols() -> List[str]:
    """
    Load and return the stock symbol list.
    
    Returns:
        List[str]: List of stock symbols.
    """
    return SYMBOL_LIST.copy()


def normalize_table_name(symbol: str) -> str:
    """
    Normalize symbol name for use as MySQL table name.
    Handles special cases: NOW, ALL, KEYS, KEY, and dots.
    
    Args:
        symbol: Stock symbol (e.g., "BRK.B", "NOW", "ALL")
        
    Returns:
        str: Normalized table name (e.g., "BRKB", "NOW1", "ALL1")
    """
    # Replace dots with empty string
    name_for_table = symbol.replace(".", "")
    
    # Handle special reserved words
    if name_for_table == "NOW":
        name_for_table = "NOW1"
    elif name_for_table == "ALL":
        name_for_table = "ALL1"
    elif name_for_table == "KEYS":
        name_for_table = "KEYS1"
    elif name_for_table == "KEY":
        name_for_table = "KEY1"
    
    return name_for_table


