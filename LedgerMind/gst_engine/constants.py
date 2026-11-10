from decimal import Decimal

# Indian GST State / UT Codes
STATE_CODES = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "19": "West Bengal",
    "24": "Gujarat",
    "27": "Maharashtra",
    "29": "Karnataka",
    "33": "Tamil Nadu",
    "36": "Telangana",
    "97": "Other Territory",
}

VALID_GST_RATES = {
    Decimal("0.00"),
    Decimal("5.00"),
    Decimal("12.00"),
    Decimal("18.00"),
    Decimal("28.00"),
}