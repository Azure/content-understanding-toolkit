**Analyzer ID:** `prebuilt-tax.us.1041ScheduleK1.2025`

**Description:** Extract tax US 1041 Schedule K-1 document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax year shown on the Schedule K-1 (Form 1041)|2025|
|`TaxYearStartDate`|`date`|`extract`|Beginning date of the estate/trust tax year (if shown)|2025-01-01|
|`TaxYearEndDate`|`date`|`extract`|Ending date of the estate/trust tax year (if shown)|2025-12-31|
|`EstateOrTrust`|`object`|`generate`|Part I information about the estate or trust (Schedule K-1 Form 1041)||
|`EstateOrTrust.EIN`|`string`|`extract`|Estate or trust employer identification number (EIN)|12-3456789|
|`EstateOrTrust.Name`|`string`|`extract`|Estate or trust name as printed|Evergreen Family Trust|
|`EstateOrTrust.Fiduciary`|`object`|`generate`|Fiduciary (trustee/executor) information and mailing address as shown in Part I||
|`EstateOrTrust.Fiduciary.Name`|`string`|`extract`|Fiduciary name (trustee/executor) as printed|Pat Lee, Trustee|
|`EstateOrTrust.Fiduciary.Address`|`string`|`extract`|Fiduciary mailing address|456 Pine St, Portland, OR 97204|
|`EstateOrTrust.Form1041TFilingStatus`|`object`|`generate`|Form 1041-T filing status checkbox and filed date (if shown)||
|`EstateOrTrust.Form1041TFilingStatus.IsForm1041TFiled`|`boolean`|`extract`|Indicator that Form 1041-T was filed (if this checkbox/field is present)|false|
|`EstateOrTrust.Form1041TFilingStatus.FiledDate`|`date`|`extract`|Date associated with the Form 1041-T filed indicator (if provided)|2025-04-15|
|`EstateOrTrust.IsFinalForm1041`|`boolean`|`extract`|Indicator that this is the final Form 1041 for the estate or trust|true|
|`Beneficiary`|`object`|`generate`|Part II information about the beneficiary (Schedule K-1 Form 1041)||
|`Beneficiary.IdentifyingNumber`|`string`|`extract`|Beneficiary identifying number (SSN/ITIN/EIN) as printed|123-45-6789|
|`Beneficiary.Name`|`string`|`extract`|Beneficiary name as printed|Casey Lee|
|`Beneficiary.Address`|`string`|`extract`|Beneficiary mailing address|789 Oak Ave, San Jose, CA 95112|
|`Beneficiary.ResidencyStatus`|`array`|`generate`|Whether the beneficiary is marked as domestic or foreign (Part II checkbox). This field can have one or more of the following values: 'DomesticBeneficiary', 'ForeignBeneficiary'||
|`Beneficiary.ResidencyStatus.*`|`string`|`extract`||DomesticBeneficiary|
|`IsFinalK1`|`boolean`|`extract`|Indicator that this K-1 is marked as final|true|
|`IsAmendedK1`|`boolean`|`extract`|Indicator that this K-1 is marked as amended|false|
|`BeneficiaryShare`|`object`|`generate`|Part III information about the beneficiary's share of income, deductions, credits, and other items. (Schedule K-1 Form 1041)||
|`BeneficiaryShare.InterestIncome`|`number`|`extract`|Interest income allocated to the beneficiary|850.25|
|`BeneficiaryShare.OrdinaryDividends`|`number`|`extract`|Ordinary dividends allocated to the beneficiary|1200|
|`BeneficiaryShare.QualifiedDividends`|`number`|`extract`|Qualified dividends included in ordinary dividends (if reported)|900|
|`BeneficiaryShare.NetShortTermCapitalGain`|`number`|`extract`|Net short-term capital gain allocated to the beneficiary|250|
|`BeneficiaryShare.NetLongTermCapitalGain`|`number`|`extract`|Net long-term capital gain allocated to the beneficiary|1750|
|`BeneficiaryShare.RateGain28Percent`|`number`|`extract`|28% gain (if reported)|0|
|`BeneficiaryShare.UnrecapturedSection1250Gain`|`number`|`extract`|Unrecaptured section 1250 gain amount, if separately stated|420|
|`BeneficiaryShare.OtherPortfolioAndNonbusinessIncome`|`number`|`extract`|Other portfolio and nonbusiness income allocated to the beneficiary|75|
|`BeneficiaryShare.OrdinaryBusinessIncome`|`number`|`extract`|Ordinary business income allocated to the beneficiary|5400|
|`BeneficiaryShare.NetRentalRealEstateIncome`|`number`|`extract`|Net rental real estate income allocated to the beneficiary|-1250|
|`BeneficiaryShare.OtherRentalIncome`|`number`|`extract`|Other rental income allocated to the beneficiary|300|
|`BeneficiaryShare.DirectlyApportionedDeductionItems`|`array`|`generate`|Directly apportioned deductions reported with a code and amount||
|`BeneficiaryShare.DirectlyApportionedDeductionItems.*`|`object`|`generate`|||
|`BeneficiaryShare.DirectlyApportionedDeductionItems.*.Code`|`string`|`extract`|Code shown for the directly apportioned deduction|A|
|`BeneficiaryShare.DirectlyApportionedDeductionItems.*.Amount`|`number`|`extract`|Amount associated with the directly apportioned deduction code|325.75|
|`BeneficiaryShare.DirectlyApportionedDeductionItems.*.StatementReference`|`string`|`extract`|Statement reference for the directly apportioned deduction item|STMT|
|`BeneficiaryShare.EstateTaxDeduction`|`number`|`extract`|Estate tax deduction amount (if reported) allocated to the beneficiary|125|
|`BeneficiaryShare.FinalYearDeductionItems`|`array`|`generate`|Final-year deductions reported with a code and amount||
|`BeneficiaryShare.FinalYearDeductionItems.*`|`object`|`generate`|||
|`BeneficiaryShare.FinalYearDeductionItems.*.Code`|`string`|`extract`|Code shown for the final-year deduction|A|
|`BeneficiaryShare.FinalYearDeductionItems.*.Amount`|`number`|`extract`|Amount associated with the final-year deduction code|780|
|`BeneficiaryShare.FinalYearDeductionItems.*.StatementReference`|`string`|`extract`|Statement reference for the final-year deduction item|STMT|
|`BeneficiaryShare.AlternativeMinimumTaxAdjustmentItems`|`array`|`generate`|Alternative minimum tax (AMT) adjustment items reported with a code and amount||
|`BeneficiaryShare.AlternativeMinimumTaxAdjustmentItems.*`|`object`|`generate`|||
|`BeneficiaryShare.AlternativeMinimumTaxAdjustmentItems.*.Code`|`string`|`extract`|Code shown for the AMT adjustment item|A|
|`BeneficiaryShare.AlternativeMinimumTaxAdjustmentItems.*.Amount`|`number`|`extract`|Amount associated with the AMT adjustment item code|1500|
|`BeneficiaryShare.AlternativeMinimumTaxAdjustmentItems.*.StatementReference`|`string`|`extract`|Statement reference for the AMT adjustment item|STMT|
|`BeneficiaryShare.CreditsAndCreditRecaptureItems`|`array`|`generate`|Credits and credit recapture items reported with a code and amount||
|`BeneficiaryShare.CreditsAndCreditRecaptureItems.*`|`object`|`generate`|||
|`BeneficiaryShare.CreditsAndCreditRecaptureItems.*.Code`|`string`|`extract`|Code shown for the credit/recapture item|A|
|`BeneficiaryShare.CreditsAndCreditRecaptureItems.*.Amount`|`number`|`extract`|Amount associated with the credit/recapture item code|100|
|`BeneficiaryShare.CreditsAndCreditRecaptureItems.*.StatementReference`|`string`|`extract`|Statement reference for the credit/recapture item|STMT|
|`BeneficiaryShare.OtherInformationItems`|`array`|`generate`|Other information items reported with a code and amount/value||
|`BeneficiaryShare.OtherInformationItems.*`|`object`|`generate`|||
|`BeneficiaryShare.OtherInformationItems.*.Code`|`string`|`extract`|Code shown for the other information item|A|
|`BeneficiaryShare.OtherInformationItems.*.Amount`|`number`|`extract`|Amount/value associated with the other information item code|250|
|`BeneficiaryShare.OtherInformationItems.*.StatementReference`|`string`|`extract`|Statement reference for the other information item|STMT|
