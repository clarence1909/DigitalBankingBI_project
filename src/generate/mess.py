"""Real-world mess: the inconsistent labels each source system uses.

Every variant here must appear in a reference map in data/reference/, and a
data quality check fails if staging meets a label it cannot map.
"""

import numpy as np

CHANNEL_VARIANTS = {
    "organic": ["organic", "(direct)", "app_store", "play_store", "Organic"],
    "google_search": ["google", "Google Ads", "google_search", "GOOGLE", "adwords"],
    "meta_ads": ["facebook", "Facebook", "instagram", "fb", "meta", "IG"],
    "tiktok": ["tiktok", "TikTok", "tik_tok", "TIKTOK"],
    "referral": ["referral", "Referral", "refer_a_friend", "friend_invite"],
    "affiliate": ["affiliate", "Affiliate", "cashback_partner", "AFFILIATE "],
}

DEVICE_OS_VARIANTS = {"android": ["android", "Android", "ANDROID"], "ios": ["ios", "iOS", "IOS"]}

STATE_WEIGHTS = {
    "Selangor": 0.26, "Kuala Lumpur": 0.16, "Johor": 0.11, "Penang": 0.08, "Perak": 0.06,
    "Sarawak": 0.06, "Sabah": 0.05, "Kedah": 0.04, "Negeri Sembilan": 0.035, "Melaka": 0.03,
    "Pahang": 0.03, "Kelantan": 0.03, "Terengganu": 0.025, "Putrajaya": 0.01,
    "Perlis": 0.005, "Labuan": 0.005,
}
STATE_VARIANTS = {
    "Selangor": ["Selangor", "SELANGOR", "Selangor Darul Ehsan"],
    "Kuala Lumpur": ["Kuala Lumpur", "W.P. Kuala Lumpur", "KL", "WP Kuala Lumpur"],
    "Johor": ["Johor", "Johore", "JOHOR", "Johor Darul Takzim"],
    "Penang": ["Pulau Pinang", "Penang", "P. Pinang", "PENANG"],
    "Perak": ["Perak", "PERAK"],
    "Sarawak": ["Sarawak", "SARAWAK"],
    "Sabah": ["Sabah", "SABAH"],
    "Kedah": ["Kedah"],
    "Negeri Sembilan": ["Negeri Sembilan", "N. Sembilan", "Negri Sembilan"],
    "Melaka": ["Melaka", "Malacca"],
    "Pahang": ["Pahang"],
    "Kelantan": ["Kelantan"],
    "Terengganu": ["Terengganu"],
    "Putrajaya": ["Putrajaya", "W.P. Putrajaya"],
    "Perlis": ["Perlis"],
    "Labuan": ["Labuan", "W.P. Labuan"],
}

EMPLOYMENT_VARIANTS = {
    "salaried": ["Salaried", "SALARIED", "salaried"],
    "self_employed": ["Self-employed", "SELF EMPLOYED", "self_employed"],
    "student": ["Student", "STUDENT"],
    "retired": ["Retired"],
    "not_working": ["Not working", "Unemployed"],
}

# Ledger transaction codes changed when the posting engine was upgraded
POSTING_ENGINE_UPGRADE = np.datetime64("2025-06-01")
TXN_CODES = {
    # txn type: (legacy code, new code)
    "salary": ("SALARY_CREDIT", "SAL"),
    "duitnow_in": ("DUITNOW_IN", "DNI"),
    "duitnow_out": ("DUITNOW_OUT", "DNO"),
    "bill_payment": ("BILL_PAYMENT", "BIL"),
    "card_purchase": ("CARD_PURCHASE", "CRD"),
    "interest": ("INTEREST_CREDIT", "INT"),
    "fd_placement": ("FD_PLACEMENT", "FDP"),
    "fd_maturity": ("FD_MATURITY", "FDM"),
    "fd_rollover": ("FD_ROLLOVER", "FDR"),
    "pf_disbursement": ("PF_DISBURSEMENT", "PFD"),
    "pf_repayment": ("PF_REPAYMENT", "PFR"),
}

CARD_STATUS_VARIANTS = {
    "APPROVED": ["APPROVED", "Approved", "approved", "APPR"],
    "DECLINED": ["DECLINED", "Declined", "DECL"],
    "REVERSED": ["REVERSED", "Reversed", "REV"],
}
ENTRY_MODE_VARIANTS = {
    "CONTACTLESS": ["CONTACTLESS", "contactless", "CTLS"],
    "CHIP": ["CHIP", "chip", "EMV"],
    "ECOM": ["ECOM", "E-COM", "online", "ecommerce"],
}
ONLINE_MCCS = {5399, 4899, 4511}

PRODUCT_CODE_VARIANTS = {
    "SAV-01": ["SAV-01", "SAV01", "sav-01"],
    "FD-06M": ["FD-06M", "FD06M"],
    "FD-12M": ["FD-12M", "FD12M"],
    "FD-RAYA25": ["FD-RAYA25"],
    "DC-01": ["DC-01", "DC01"],
}


def pick_variants(rng, standard_values, variants, dominant=0.6):
    """Replace each standard value with one of its raw variants.

    The first variant is the most common; the rest share what is left.
    """
    standard_values = np.asarray(standard_values, dtype=object)
    out = np.empty(len(standard_values), dtype=object)
    for std, options in variants.items():
        idx = np.flatnonzero(standard_values == std)
        if len(idx) == 0:
            continue
        if len(options) == 1:
            out[idx] = options[0]
            continue
        rest = (1 - dominant) / (len(options) - 1)
        weights = [dominant] + [rest] * (len(options) - 1)
        out[idx] = np.asarray(options, dtype=object)[rng.choice(len(options), size=len(idx), p=weights)]
    return out


def txn_code_for(txn_type, ts):
    """Legacy long codes before the posting engine upgrade, short codes after."""
    legacy, new = TXN_CODES[txn_type]
    ts = np.asarray(ts)
    return np.where(ts < POSTING_ENGINE_UPGRADE, legacy, new).astype(object)
