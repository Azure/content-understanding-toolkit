**Analyzer ID:** `prebuilt-idDocument`

**Description:** A composed prebuilt analyzer for various ID documentation types.

| Category | Analyzer ID | Description |
|:------|:-----|:--------|
|`idDocument.generic`|[`prebuilt-idDocument.generic`](idDocument.generic.md)|Government-issued identity cards or permits other than passports; usually plastic cards or paper permits. Examples: driver's license/learner's permit, national ID card, residence/PR permit, military ID, social security card, state/territory photo ID, Aadhaar. Typical features: person's name, photo (SSN may lack), date of birth, ID/license/UIN number, issuing authority logo/seal, issue/expiry dates; may include address, signature, license class/restrictions; barcodes/QR codes or MRZ not starting with 'P<'. Excludes anything explicitly labeled 'Passport' or visa/stamp pages.|
|`idDocument.passport`|[`prebuilt-idDocument.passport`](idDocument.passport.md)|National passports (booklets) and passport cards. Strong cues: the word 'Passport' on cover or data page; data page with holder photo and fields like Passport No., Nationality, Date of Birth, Sex, Place of Birth, Date of Issue/Expiry, Authority, signature; two-line MRZ at bottom starting with 'P<'. Includes documents explicitly labeled 'Passport Card'. Excludes visas, entry/exit stamps, and covers shown alone without a visible data page.|
|`other`|`prebuilt-documentFields`|Any document not matching the category above. Use other for partial excerpts or heavily redacted pages where the form type cannot be confidently identified.|
