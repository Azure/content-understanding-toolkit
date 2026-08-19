| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax year shown on Form M1|2025|
|`Taxpayer`|`object`|`generate`|Taxpayer identification information shown at the top of Form M1||
|`Taxpayer.FirstNameAndInitial`|`string`|`extract`|Taxpayer first name and middle initial as printed|John A|
|`Taxpayer.LastName`|`string`|`extract`|Taxpayer last name as printed|Smith|
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer Social Security Number|123-45-6789|
|`Taxpayer.BirthDate`|`date`|`extract`|Taxpayer date of birth|1980-03-15|
|`Spouse`|`object`|`generate`|Spouse identification information (if filing jointly)||
|`Spouse.FirstNameAndInitial`|`string`|`extract`|Spouse first name and middle initial as printed|Jane B|
|`Spouse.LastName`|`string`|`extract`|Spouse last name as printed|Smith|
|`Spouse.SSN`|`string`|`extract`|Spouse Social Security Number|987-65-4321|
|`Spouse.BirthDate`|`date`|`extract`|Spouse date of birth|1982-07-22|
|`Address`|`string`|`extract`|Current home address including city/state/ZIP/county|456 Elm St, Minneapolis, MN 55401|
|`AddressStatus`|`array`|`generate`|Checkbox indicating whether the address is new or foreign. This field can have one or more of the following values: 'New', 'Foreign'||
|`AddressStatus.*`|`string`|`extract`||New|
|`FederalFiling`|`object`|`generate`|Federal filing status section||
|`FederalFiling.Status`|`array`|`generate`|2025 federal filing status (place an X in one box). This field can have one or more of the following values: 'Single', 'MarriedFilingJointly', 'MarriedFilingSeparately', 'HeadOfHousehold', 'QualifyingSurvivingSpouse'||
|`FederalFiling.Status.*`|`string`|`extract`||MarriedFilingJointly|
|`FederalFiling.SpouseName`|`string`|`extract`|Spouse name shown in the filing status section (for Married Filing Separately or Qualifying Surviving Spouse)|Jane Smith|
|`FederalFiling.SpouseSSN`|`string`|`extract`|Spouse SSN shown in the filing status section|987-65-4321|
|`ElectionsCampaignFund`|`object`|`generate`|State Elections Campaign Fund section||
|`ElectionsCampaignFund.TaxpayerCode`|`string`|`extract`|Political party code for the State Elections Campaign Fund (taxpayer)|12|
|`ElectionsCampaignFund.SpouseCode`|`string`|`extract`|Political party code for the State Elections Campaign Fund (spouse)|99|
|`WagesSalariesTipsEtc`|`number`|`extract`|Wages, salaries, tips, etc. from your federal return (line A)|52000|
|`IRAPensionsAndAnnuities`|`number`|`extract`|IRA, pensions, and annuities from your federal return (line B)|3500|
|`Unemployment`|`number`|`extract`|Unemployment compensation from your federal return (line C)|0|
|`FederalTaxableIncome`|`number`|`extract`|Federal taxable income from your federal return (line D)|45000|
|`SocialSecurityBenefits`|`number`|`extract`|Social Security benefits from your federal return (line E)|12000|
|`TaxableSocialSecurityBenefits`|`number`|`extract`|Taxable Social Security benefits from your federal return (line F)|10200|
|`FederalAdjustedGrossIncome`|`number`|`extract`|Federal adjusted gross income from line 11 of federal Form 1040/1040-SR (line 1)|55000|
|`AdditionsToIncome`|`number`|`extract`|Additions to income from line 10 of Schedule M1M and line 9 of Schedule M1MB (line 2)|500|
|`AddLines1And2`|`number`|`extract`|Sum of lines 1 and 2 (line 3)|55500|
|`ItemizedDeductionsOrStandardDeduction`|`number`|`extract`|Itemized deductions from Schedule M1SA or your standard deduction (line 4)|15000|
|`Exemptions`|`number`|`extract`|Exemptions from Schedule M1DQC (line 5)|4050|
|`StateIncomeTaxRefund`|`number`|`extract`|State income tax refund from line 1 of federal Schedule 1 (line 6)|200|
|`SubtractionsFromScheduleM1MAndM1MB`|`number`|`extract`|Subtractions from line 40 of Schedule M1M and line 22 of Schedule M1MB (line 7)|1000|
|`TotalSubtractions`|`number`|`extract`|Total subtractions — sum of lines 4 through 7 (line 8)|20250|
|`MinnesotaTaxableIncome`|`number`|`extract`|Minnesota taxable income — line 3 minus line 8; if zero or less, leave blank (line 9)|35250|
|`TaxFromTableOrSchedules`|`number`|`extract`|Tax from the table or schedules in the Form M1 instructions (line 10)|2100|
|`AlternativeMinimumTax`|`number`|`extract`|Alternative minimum tax (enclose Schedule M1MT) (line 11)|0|
|`AddLines10And11`|`number`|`extract`|Sum of lines 10 and 11 (line 12)|2100|
|`TaxAfterResidencyAdjustment`|`number`|`extract`|Full-year residents enter the amount from line 12; part-year residents and nonresidents enter the amount from Schedule M1NR line 32 (line 13)|2100|
|`NonresidentScheduleM1NRLine28`|`number`|`extract`|Part-year residents and nonresidents enter the amount from Schedule M1NR line 28 (line 13a)|0|
|`NonresidentScheduleM1NRLine29`|`number`|`extract`|Part-year residents and nonresidents enter the amount from Schedule M1NR line 29 (line 13b)|0|
|`OtherTaxes`|`object`|`generate`|Other taxes and applicable schedule checkboxes (line 14a)||
|`OtherTaxes.Amount`|`number`|`extract`|Other taxes such as recapture amounts and tax on lump-sum distributions (line 14a)|0|
|`OtherTaxes.Type`|`array`|`generate`|Applicable schedule type for other taxes (line 14a). This field can have one or more of the following values: 'ScheduleM1HOME', 'ScheduleM1529', 'ScheduleM1LS', 'ScheduleNIIT'||
|`OtherTaxes.Type.*`|`string`|`extract`||ScheduleM1HOME|
|`RepaymentOfAdvanceChildTaxCredit`|`number`|`extract`|Repayment of advance child tax credit (line 14b)|0|
|`TaxBeforeCredits`|`number`|`extract`|Tax before credits — sum of lines 13, 14a, and 14b (line 15)|2100|
|`NonrefundableCredits`|`number`|`extract`|Nonrefundable credits from line 19 of Schedule M1C (line 16)|0|
|`SubtractLine16FromLine15`|`number`|`extract`|Line 15 minus line 16; if zero or less, leave blank (line 17)|2100|
|`NongameWildlifeFundContribution`|`number`|`extract`|Nongame Wildlife Fund contribution — reduces refund or increases amount owed (line 18)|0|
|`AddLines17And18`|`number`|`extract`|Sum of lines 17 and 18 (line 19)|2100|
|`MinnesotaIncomeTaxWithheld`|`number`|`extract`|Minnesota income tax withheld from Forms W-2, 1099, and W-2G (line 20)|2500|
|`EstimatedTaxAndExtensionPayments`|`number`|`extract`|Minnesota estimated tax and extension payments made for 2025 (line 21)|0|
|`RefundableCredits`|`number`|`extract`|Refundable credits from line 14 of Schedule M1REF (line 22)|0|
|`TotalPayments`|`number`|`extract`|Total payments — sum of lines 20 through 22 (line 23)|2500|
|`TotalRefund`|`number`|`extract`|Refund — if line 23 is more than line 19, subtract line 19 from line 23 (line 24)|400|
|`DirectDeposit`|`object`|`generate`|Direct deposit information for refund (line 25)||
|`DirectDeposit.AccountType`|`array`|`generate`|Account type for direct deposit of refund (line 25). This field can have one or more of the following values: 'Checking', 'Savings'||
|`DirectDeposit.AccountType.*`|`string`|`extract`||Checking|
|`DirectDeposit.RoutingNumber`|`string`|`extract`|Bank routing number for direct deposit of refund (line 25)|091000019|
|`DirectDeposit.AccountNumber`|`string`|`extract`|Bank account number for direct deposit of refund (line 25)|123456789012|
|`AmountYouOwe`|`number`|`extract`|Amount you owe — if line 19 is more than line 23, subtract line 23 from line 19 (line 26)|0|
|`PenaltyAmountFromScheduleM15`|`number`|`extract`|Penalty amount from Schedule M15 (line 27)|0|
|`PenaltyAndInterest`|`number`|`extract`|Penalty and interest (line 28)|0|
|`RefundAmountToReceive`|`number`|`extract`|Amount from line 24 you want sent to you (line 29)|400|
|`RefundAppliedToNextYearEstimatedTax`|`number`|`extract`|Amount from line 24 you want applied to your 2026 estimated tax (line 30)|0|
|`TaxpayerInformation`|`object`|`generate`|Taxpayer and spouse signature block at the bottom of Form M1||
|`TaxpayerInformation.Signature`|`string`|`classify`|Taxpayer signature presence classification (signed \| unsigned \| notFound)|signed|
|`TaxpayerInformation.SpouseSignature`|`string`|`classify`|Spouse signature presence classification (signed \| unsigned \| notFound)|signed|
|`TaxpayerInformation.SignatureDate`|`date`|`extract`|Date of taxpayer/spouse signature|2026-04-15|
|`TaxpayerInformation.DaytimePhone`|`string`|`extract`|Taxpayer daytime phone number|612-555-0100|
|`TaxpayerInformation.Email`|`string`|`extract`|Taxpayer email address|john.smith@example.com|
|`PaidPreparerInformation`|`object`|`generate`|Paid preparer information block at the bottom of Form M1||
|`PaidPreparerInformation.Signature`|`string`|`classify`|Paid preparer signature presence classification (signed \| unsigned \| notFound)|signed|
|`PaidPreparerInformation.SignatureDate`|`date`|`extract`|Date of paid preparer signature|2026-04-10|
|`PaidPreparerInformation.PTINOrVITATCE`|`string`|`extract`|Paid preparer PTIN or VITA/TCE identification number|P01234567|
|`PaidPreparerInformation.DaytimePhone`|`string`|`extract`|Paid preparer daytime phone number|651-555-0200|
|`PaidPreparerInformation.Email`|`string`|`extract`|Paid preparer email address|maria.johnson@taxprep.com|
|`IsRefusingElectronicFiling`|`boolean`|`extract`|Checkbox to refuse paid preparer filing the return electronically (page 2)|false|
|`IsAuthorizingReturnDiscussionWithPreparer`|`boolean`|`extract`|Checkbox to authorize the government to discuss this return with the preparer or third-party designee (page 2)|true|
|`IsFilingForNetInvestmentIncomeTax`|`boolean`|`extract`|Checkbox indicating filing this return for net investment income tax requirements (page 2)|false|
|`IsApprovingTaxInfoSharingWithMNsure`|`boolean`|`extract`|Checkbox to approve the government sharing tax information with MNsure (page 2)|false|
