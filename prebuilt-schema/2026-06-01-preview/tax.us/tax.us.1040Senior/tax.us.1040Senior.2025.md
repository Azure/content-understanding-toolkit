**Analyzer ID:** `prebuilt-tax.us.1040Senior.2025`

**Description:** Extract tax US 1040 senior document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-SR.|2025|
|`OtherTaxYearStartDate`|`date`|`extract`|Start date for the other tax year period.|2025-01-01|
|`OtherTaxYearEndDate`|`date`|`extract`|End date for the other tax year period.|2025-06-30|
|`FiledPursuantToAutomaticExtension`|`boolean`|`extract`|Indicator that the return was filed pursuant to an automatic extension.|false|
|`HasCombatZone`|`boolean`|`extract`|Indicator that the combat zone section is filled.|false|
|`CombatZone`|`string`|`extract`|Combat zone name if provided.|Afghanistan|
|`IsDeceased`|`boolean`|`extract`|Indicator that the taxpayer or spouse is marked as deceased.|false|
|`TaxpayerDeceaseDate`|`date`|`extract`|Taxpayer date of death if provided.|2025-03-14|
|`SpouseDeceaseDate`|`date`|`extract`|Spouse date of death if provided.|2025-03-14|
|`HasOtherInformation`|`boolean`|`extract`|Indicator that the other information section is present.|false|
|`OtherInformation`|`string`|`extract`|Other information text if provided.|See attached statement|
|`Taxpayer`|`object`|`generate`|Taxpayer information extracted from the return.||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.LastName`|`string`|`extract`|Taxpayer last name as written on the form.|Smith|
|`Taxpayer.FirstNameAndMiddleInitial`|`string`|`extract`|Taxpayer first name and middle initial as written on the form.|John T|
|`Taxpayer.Address`|`string`|`extract`|Taxpayer address.|123 Fremont Ave Apt 55|
|`Taxpayer.ForeignCountryName`|`string`|`extract`|Taxpayer foreign country name.|Germany|
|`Taxpayer.ForeignProvinceStateOrCounty`|`string`|`extract`|Taxpayer foreign province/state/county.|Hamburg|
|`Taxpayer.ForeignPostalCode`|`string`|`extract`|Taxpayer foreign postal code.|20095|
|`Spouse`|`object`|`generate`|Spouse information extracted from the return when present.||
|`Spouse.SSN`|`string`|`extract`|Spouse social security number.|987-65-4321|
|`Spouse.LastName`|`string`|`extract`|Spouse last name as written on the form.|Smith|
|`Spouse.FirstNameAndMiddleInitial`|`string`|`extract`|Spouse first name and middle initial as written on the form.|Jane A|
|`Dependents`|`array`|`generate`|Dependents extracted from Form 1040-SR||
|`Dependents.*`|`object`|`generate`|||
|`Dependents.*.FirstName`|`string`|`extract`|Dependent first name as written on the form.|Elton|
|`Dependents.*.LastName`|`string`|`extract`|Dependent last name as written on the form.|Smith|
|`Dependents.*.SSN`|`string`|`extract`|Dependent social security number.|741-25-8963|
|`Dependents.*.RelationshipToFiler`|`string`|`extract`|Dependent relationship to the filer.|Son|
|`Dependents.*.LivedWithTaxpayerMoreThanHalfOfTaxYear`|`boolean`|`extract`|Indicator that the dependent lived with the taxpayer more than half of the tax year.|false|
|`Dependents.*.LivedInTheUS`|`boolean`|`extract`|Indicator that the dependent lived in the U.S.|true|
|`Dependents.*.IsStudent`|`boolean`|`extract`|Indicator that the dependent is a student.|false|
|`Dependents.*.IsDisabled`|`boolean`|`extract`|Indicator that the dependent is disabled.|false|
|`Dependents.*.CreditType`|`array`|`generate`|Selected credit(s) applicable to the dependent.||
|`Dependents.*.CreditType.*`|`string`|`extract`||Child tax credit|
|`LivedApartIfMFSorHOH`|`boolean`|`extract`|Indicator that the taxpayer lived apart if filing MFS or HOH.|false|
|`ThirdPartyDesignee`|`object`|`generate`|Third-party designee information if the taxpayer authorizes a designee.||
|`ThirdPartyDesignee.PhoneNumber`|`string`|`extract`|Third party designee phone number.|206-123-456|
|`ThirdPartyDesignee.Name`|`string`|`extract`|Third party designee name as written on the form.|John Appleseed|
|`ThirdPartyDesignee.PersonalIdentificationNumber`|`string`|`extract`|Third party designee PIN.|98765|
|`SignatureDetails`|`object`|`generate`|Signature section details including occupations, IP PINs, and contact information.||
|`SignatureDetails.TaxpayerOccupation`|`string`|`extract`|Taxpayer occupation.|Engineer|
|`SignatureDetails.TaxpayerPIN`|`string`|`extract`|Taxpayer Identity Protection PIN if provided.|789654|
|`SignatureDetails.TaxpayerPhoneNumber`|`string`|`extract`|Taxpayer phone number.|206-654-3219|
|`SignatureDetails.TaxpayerEmail`|`string`|`extract`|Taxpayer email.|john.smith@contoso.com|
|`SignatureDetails.SpouseOccupation`|`string`|`extract`|Spouse occupation.|Engineer|
|`SignatureDetails.SpousePIN`|`string`|`extract`|Spouse Identity Protection PIN if provided.|785132|
|`PaidPreparer`|`object`|`generate`|Paid preparer information if the return was prepared by a paid preparer.||
|`PaidPreparer.Name`|`string`|`extract`|Preparer name.|John Appleseed|
|`PaidPreparer.PTIN`|`string`|`extract`|Preparer PTIN.|98765|
|`PaidPreparer.IsPreparerSelfEmployed`|`boolean`|`extract`|Preparer self-employed indicator.|true|
|`PaidPreparer.FirmName`|`string`|`extract`|Preparer firm name.|Contoso Tax|
|`PaidPreparer.FirmPhoneNumber`|`string`|`extract`|Preparer firm phone number.|206-001-9876|
|`PaidPreparer.FirmAddress`|`string`|`extract`|Preparer firm address.|1 Contoso Way, Redmond WA 98052|
|`PaidPreparer.FirmEIN`|`string`|`extract`|Preparer firm EIN.|12-3456789|
|`FilingStatus`|`array`|`generate`|Selected filing status.||
|`FilingStatus.*`|`string`|`extract`||Married filing jointly|
|`SpouseName`|`string`|`extract`|Name of spouse when required.|Jane Doe|
|`QualifyingPersonName`|`string`|`extract`|Name of qualifying person when required.|Jane Doe|
|`IsNonresidentAlienOrDualStatusAlienSpouse`|`boolean`|`extract`|Nonresident alien or dual-status alien spouse checkbox.|false|
|`NonresidentAlienOrDualStatusAlienSpouseName`|`string`|`extract`|Name of nonresident alien or dual-status alien spouse when applicable.|Jane A Smith|
|`MainHomeWasMoreThanHalfOfTaxYear`|`boolean`|`extract`|Indicator that the main home was maintained for more than half of the tax year.|false|
|`PresidentialElectionCampaign`|`array`|`generate`|Selected Presidential Election Campaign checkbox(es).||
|`PresidentialElectionCampaign.*`|`string`|`extract`||You|
|`DigitalAssets`|`array`|`generate`|Digital assets question selection.||
|`DigitalAssets.*`|`string`|`extract`||No|
|`HasMoreThanFourDependents`|`boolean`|`extract`|Indicator if more than four dependents box is checked.|false|
|`Box1a`|`number`|`extract`|Box 1a extracted from Form 1040-SR.|987654|
|`Box1b`|`number`|`extract`|Box 1b extracted from Form 1040-SR.|654|
|`Box1c`|`number`|`extract`|Box 1c extracted from Form 1040-SR.|123|
|`Box1d`|`number`|`extract`|Box 1d extracted from Form 1040-SR.|741|
|`Box1e`|`number`|`extract`|Box 1e extracted from Form 1040-SR.|963|
|`Box1f`|`number`|`extract`|Box 1f extracted from Form 1040-SR.|951|
|`Box1g`|`number`|`extract`|Box 1g extracted from Form 1040-SR.|123|
|`Box1h`|`number`|`extract`|Box 1h extracted from Form 1040-SR.|987|
|`Box1hExtraInfo`|`string`|`extract`|Box 1h extra info extracted from Form 1040-SR.|987.00|
|`Box1i`|`number`|`extract`|Box 1i extracted from Form 1040-SR (nontaxable combat pay election).|236|
|`Box1z`|`number`|`extract`|Box 1z extracted from Form 1040-SR.|127|
|`Box2a`|`number`|`extract`|Box 2a extracted from Form 1040-SR.|963|
|`Box2b`|`number`|`extract`|Box 2b extracted from Form 1040-SR.|654|
|`Box3a`|`number`|`extract`|Box 3a extracted from Form 1040-SR.|357|
|`Box3b`|`number`|`extract`|Box 3b extracted from Form 1040-SR.|951|
|`Box3c`|`array`|`generate`|Box 3c extracted from Form 1040-SR.||
|`Box3c.*`|`string`|`extract`||Line3a|
|`Box4a`|`number`|`extract`|Box 4a extracted from Form 1040-SR.|986|
|`Box4b`|`number`|`extract`|Box 4b extracted from Form 1040-SR.|643|
|`Box4c`|`array`|`generate`|Box 4c extracted from Form 1040-SR.||
|`Box4c.*`|`string`|`extract`||Rollover|
|`Box4cOther`|`string`|`extract`|Box 4c other extracted from Form 1040-SR.|Other|
|`Box5a`|`number`|`extract`|Box 5a extracted from Form 1040-SR.|315|
|`Box5b`|`number`|`extract`|Box 5b extracted from Form 1040-SR.|213|
|`Box5c`|`array`|`generate`|Box 5c extracted from Form 1040-SR.||
|`Box5c.*`|`string`|`extract`||Rollover|
|`Box5cOther`|`string`|`extract`|Box 5c other extracted from Form 1040-SR.|Other|
|`Box6a`|`number`|`extract`|Box 6a extracted from Form 1040-SR.|123|
|`Box6b`|`number`|`extract`|Box 6b extracted from Form 1040-SR.|846|
|`Box6cIsChecked`|`boolean`|`extract`|Lump-sum election method checkbox (6c).|true|
|`Box6dIsChecked`|`boolean`|`extract`|Married filing separately and lived apart checkbox (6d).|false|
|`Box7a`|`number`|`extract`|Box 7a extracted from Form 1040-SR.|684|
|`Box7b`|`array`|`generate`|Box 7b extracted from Form 1040-SR.||
|`Box7b.*`|`string`|`extract`||ScheduleDNotRequired|
|`Box7bAmount`|`number`|`extract`|Box 7b amount extracted from Form 1040-SR.|0|
|`Box8`|`number`|`extract`|Box 8 extracted from Form 1040-SR.|987|
|`Box9`|`number`|`extract`|Box 9 extracted from Form 1040-SR (total income).|213|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-SR (adjustments to income).|136|
|`Box11a`|`number`|`extract`|Box 11a extracted from Form 1040-SR (adjusted gross income).|943|
|`Box11b`|`number`|`extract`|Box 11b extracted from Form 1040-SR (adjusted gross income).|943|
|`Box12a`|`array`|`generate`|Someone can claim you/your spouse status selection.||
|`Box12a.*`|`string`|`extract`||TaxpayerAsDependent|
|`Box12bIsChecked`|`boolean`|`extract`|Box 12b checkbox extracted from Form 1040-SR.|false|
|`Box12cIsChecked`|`boolean`|`extract`|Box 12c checkbox extracted from Form 1040-SR.|false|
|`Box12dYou`|`array`|`generate`|Taxpayer age/blindness selection.||
|`Box12dYou.*`|`string`|`extract`||Above64|
|`Box12dSpouse`|`array`|`generate`|Spouse age/blindness selection.||
|`Box12dSpouse.*`|`string`|`extract`||Blind|
|`Box12e`|`number`|`extract`|Box 12e extracted from Form 1040-SR (standard or itemized deductions).|179|
|`Box13a`|`number`|`extract`|Box 13a extracted from Form 1040-SR (QBI deduction).|246|
|`Box13b`|`number`|`extract`|Box 13b extracted from Form 1040-SR (QBI deduction).|0|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-SR.|217|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-SR (taxable income).|269|
|`Box16FromForm`|`array`|`generate`|Forms contributing to line 16.||
|`Box16FromForm.*`|`string`|`extract`||8814|
|`Box16OtherFormNumber`|`string`|`extract`|Other form number for line 16 when 'Other' is selected.|4972|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-SR (tax).|156|
|`Box17`|`number`|`extract`|Box 17 extracted from Form 1040-SR.|241|
|`Box18`|`number`|`extract`|Box 18 extracted from Form 1040-SR.|979.33|
|`Box19`|`number`|`extract`|Box 19 extracted from Form 1040-SR.|333.11|
|`Box20`|`number`|`extract`|Box 20 extracted from Form 1040-SR.|123|
|`Box21`|`number`|`extract`|Box 21 extracted from Form 1040-SR.|138.44|
|`Box22`|`number`|`extract`|Box 22 extracted from Form 1040-SR.|198|
|`Box23`|`number`|`extract`|Box 23 extracted from Form 1040-SR.|297|
|`Box24`|`number`|`extract`|Box 24 extracted from Form 1040-SR (total tax).|548|
|`Box25a`|`number`|`extract`|Box 25a extracted from Form 1040-SR.|854|
|`Box25b`|`number`|`extract`|Box 25b extracted from Form 1040-SR.|596|
|`Box25c`|`number`|`extract`|Box 25c extracted from Form 1040-SR.|216|
|`Box25d`|`number`|`extract`|Box 25d extracted from Form 1040-SR.|211|
|`Box26`|`number`|`extract`|Box 26 extracted from Form 1040-SR.|477.33|
|`Box26SSN`|`string`|`extract`|Box 26 SSN extracted from Form 1040-SR.|123-45-6789|
|`Box27a`|`number`|`extract`|Box 27a extracted from Form 1040-SR (EIC).|351|
|`Box27bIsChecked`|`boolean`|`extract`|Box 27b extracted from Form 1040-SR (EIC).|false|
|`Box27cIsChecked`|`boolean`|`extract`|Box 27c extracted from Form 1040-SR (EIC).|false|
|`Box28`|`number`|`extract`|Box 28 extracted from Form 1040-SR.|211|
|`Box28IsChecked`|`boolean`|`extract`|Box 28 checkbox extracted from Form 1040-SR (additional child tax credit).|false|
|`Box29`|`number`|`extract`|Box 29 extracted from Form 1040-SR.|246|
|`Box30`|`number`|`extract`|Box 30 extracted from Form 1040-SR.|489|
|`Box31`|`number`|`extract`|Box 31 extracted from Form 1040-SR.|528|
|`Box32`|`number`|`extract`|Box 32 extracted from Form 1040-SR.|126|
|`Box33`|`number`|`extract`|Box 33 extracted from Form 1040-SR.|158|
|`Box34`|`number`|`extract`|Box 34 extracted from Form 1040-SR (overpaid).|788|
|`Box35a`|`number`|`extract`|Box 35a extracted from Form 1040-SR (refund amount).|123.98|
|`Box35aIsChecked`|`boolean`|`extract`|Form 8888 attached checkbox (line 35a).|true|
|`Box35b`|`string`|`extract`|Routing number (line 35b).|123456789|
|`Box35c`|`array`|`generate`|Account type selection (Checking/Savings).||
|`Box35c.*`|`string`|`extract`||Checking|
|`Box35d`|`string`|`extract`|Account number (line 35d).|98745632145699874|
|`Box36`|`number`|`extract`|Box 36 extracted from Form 1040-SR.|456|
|`Box37`|`number`|`extract`|Box 37 extracted from Form 1040-SR (amount you owe).|123|
|`Box38`|`number`|`extract`|Box 38 extracted from Form 1040-SR (estimated tax penalty).|125|
|`ThirdPartyDesigneeSelection`|`array`|`generate`|Third party designee question selection.||
|`ThirdPartyDesigneeSelection.*`|`string`|`extract`||Yes|
