| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-COMBO.|2025|
|`Payer`|`object`|`generate`|||
|`Payer.TIN`|`string`|`extract`|Payer tax identification number.|98-7654321|
|`Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE LLC|
|`Payer.Address`|`string`|`extract`|Payer address.|123 WASHINGTON BLVD, SEATTLE, WA 98122|
|`Payer.PhoneNumber`|`string`|`extract`|Payer phone number.|+19876543210|
|`Recipient`|`object`|`generate`|||
|`Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|***-**-9876|
|`Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERTH|
|`Recipient.Address`|`string`|`extract`|Recipient address.|987 FREMONT AVE N, SEATTLE, WA 98103|
|`Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|XYZ-123456789|
|`Form1099B`|`object`|`generate`|||
|`Form1099B.Summaries`|`array`|`generate`|List of transaction summaries reported in the Form 1099-B||
|`Form1099B.Summaries.*`|`object`|`generate`|||
|`Form1099B.Summaries.*.Category`|`string`|`classify`|Can be one of the following: 'shortTermBasisReportedToIRS', 'shortTermBasisNotReportedToIRS', 'shortTermBasisUndetermined', 'longTermBasisReportedToIRS', 'longTermBasisNotReportedToIRS', 'longTermBasisUndetermined', 'ordinaryBasisReportedToIRS', 'ordinaryBasisNotReportedToIRS', 'ordinaryBasisUndetermined', 'undeterminedBasisReportedToIRS', 'undeterminedBasisNotReportedToIRS', 'undeterminedBasisUndetermined'.|shortTermBasisReportedToIRS|
|`Form1099B.Summaries.*.TotalProceeds`|`number`|`extract`|Total proceeds summary extracted from Form 1099-B.|654654.54|
|`Form1099B.Summaries.*.TotalCostBasis`|`number`|`extract`|Total cost basis summary extracted from Form 1099-B.|321321.21|
|`Form1099B.Summaries.*.TotalMarketDiscount`|`number`|`extract`|Total market discount summary extracted from Form 1099-B.|0|
|`Form1099B.Summaries.*.TotalWashSales`|`number`|`extract`|Total wash sales summary extracted from Form 1099-B.|2468|
|`Form1099B.Summaries.*.TotalRealizedGainOrLoss`|`number`|`extract`|Total realized gain or loss summary extracted from Form 1099-B.|9987.98|
|`Form1099B.Summaries.*.TotalFederalIncomeTaxWithheld`|`number`|`extract`|Total federal income tax withheld summary extracted from Form 1099-B.|0|
|`Form1099B.Summaries.*.TotalNetGainOrLoss`|`number`|`extract`|Total net gain or loss summary fo Form 1099-B.|123456|
|`Form1099B.Transactions`|`array`|`generate`|List of transactions reported in the Form 1099-B||
|`Form1099B.Transactions.*`|`object`|`generate`|||
|`Form1099B.Transactions.*.CUSIPNumber`|`string`|`extract`|CUSIP Number extracted from Form 1099-B.|68389X105|
|`Form1099B.Transactions.*.ApplicableForm8949Checkbox`|`string`|`extract`|Applicable Form8949 Checkbox extracted from Form 1099-B.|A|
|`Form1099B.Transactions.*.Box1a`|`string`|`extract`|Box 1a extracted from Form 1099-B.|ORACLE CORP, ORCL, 68389X105|
|`Form1099B.Transactions.*.Box1b`|`date`|`extract`|Box 1b extracted from Form 1099-B.|2025-12-01|
|`Form1099B.Transactions.*.Box1c`|`date`|`extract`|Box 1c extracted from Form 1099-B.|2025-12-24|
|`Form1099B.Transactions.*.Box1d`|`number`|`extract`|Box 1d extracted from Form 1099-B.|12.34|
|`Form1099B.Transactions.*.Box1e`|`number`|`extract`|Box 1e extracted from Form 1099-B.|98.76|
|`Form1099B.Transactions.*.Box1f`|`number`|`extract`|Box 1f extracted from Form 1099-B.|0|
|`Form1099B.Transactions.*.Box1g`|`number`|`extract`|Box 1g extracted from Form 1099-B.|0.01|
|`Form1099B.Transactions.*.Box2`|`string`|`classify`|Gain/loss terms. Can be one of the following: 'shortTermGainOrLoss', 'longTermGainOrLoss', 'ordinary', 'undetermined'.|shortTermGainOrLoss|
|`Form1099B.Transactions.*.Box3`|`string`|`classify`|Type of gain or loss. Can be one of the following: 'collectible', 'qof', 'undetermined'.|collectible|
|`Form1099B.Transactions.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-B.|0|
|`Form1099B.Transactions.*.Box5`|`boolean`|`generate`|If checked, noncovered security.|false|
|`Form1099B.Transactions.*.Box6`|`string`|`classify`|Type of proceeds. Can be one of the following: 'grossProceeds', 'netProceeds', 'undetermined'.|grossProceeds|
|`Form1099B.Transactions.*.Box7`|`boolean`|`generate`|If checked, loss is not allowed based on amount in 1d.|false|
|`Form1099B.Transactions.*.Box8`|`number`|`extract`|Profit or (loss) realized in year on closed contracts.|654321|
|`Form1099B.Transactions.*.Box9`|`number`|`extract`|Unrealized profit or (loss) on open contracts - prior year end.|0|
|`Form1099B.Transactions.*.Box10`|`number`|`extract`|Unrealized profit or (loss) on open contracts - current year end.|0|
|`Form1099B.Transactions.*.Box11`|`number`|`extract`|Aggregate profit or (loss) on contracts.|0|
|`Form1099B.Transactions.*.Box12`|`boolean`|`generate`|If checked, basis reported to IRS.|false|
|`Form1099B.Transactions.*.Box13`|`number`|`extract`|Bartering amount.|0|
|`Form1099B.Transactions.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-B||
|`Form1099B.Transactions.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099B.Transactions.*.StateTaxesWithheld.*.Box14`|`string`|`extract`|Box 14 extracted from Form 1099-B.|WA|
|`Form1099B.Transactions.*.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-B.|87654321|
|`Form1099B.Transactions.*.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-B.|123|
|`Form1099B.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-B.|false|
|`Form1099DIV`|`object`|`generate`|||
|`Form1099DIV.Summary`|`object`|`generate`|Summary of Form 1099-DIV.||
|`Form1099DIV.Summary.Box1a`|`number`|`extract`|Box 1a extracted from Form 1099-DIV.|4321.98|
|`Form1099DIV.Summary.Box1b`|`number`|`extract`|Box 1b extracted from Form 1099-DIV.|6543.21|
|`Form1099DIV.Summary.Box2a`|`number`|`extract`|Box 2a extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box2b`|`number`|`extract`|Box 2b extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box2c`|`number`|`extract`|Box 2c extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box2d`|`number`|`extract`|Box 2d extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box2e`|`number`|`extract`|Box 2e extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box2f`|`number`|`extract`|Box 2f extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box7`|`number`|`extract`|Box 7 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box8`|`string`|`extract`|Box 8 extracted from Form 1099-DIV.|U.S.|
|`Form1099DIV.Summary.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-DIV.|123.65|
|`Form1099DIV.Summary.Box13`|`number`|`extract`|Box 13 extracted from Form 1099-DIV.|0|
|`Form1099DIV.Summary.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-DIV||
|`Form1099DIV.Summary.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099DIV.Summary.StateTaxesWithheld.*.Box14`|`string`|`extract`|Box 14 extracted from Form 1099-DIV.|WA|
|`Form1099DIV.Summary.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-DIV.|123456789|
|`Form1099DIV.Summary.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-DIV.|0|
|`Form1099DIV.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-DIV.|false|
|`Form1099INT`|`object`|`generate`|||
|`Form1099INT.Summary`|`object`|`generate`|Summary of Form 1099-INT.||
|`Form1099INT.Summary.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-INT.|123.45|
|`Form1099INT.Summary.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-INT.|54321|
|`Form1099INT.Summary.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-INT.|654|
|`Form1099INT.Summary.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-INT.|987|
|`Form1099INT.Summary.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-INT.|963|
|`Form1099INT.Summary.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-INT.|753|
|`Form1099INT.Summary.Box7`|`string`|`extract`|Box 7 extracted from Form 1099-INT.|U.S.|
|`Form1099INT.Summary.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-INT.|852|
|`Form1099INT.Summary.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-INT.|973|
|`Form1099INT.Summary.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-INT.|753|
|`Form1099INT.Summary.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-INT.|741|
|`Form1099INT.Summary.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-INT.|147|
|`Form1099INT.Summary.Box13`|`number`|`extract`|Box 13 extracted from Form 1099-INT.|369|
|`Form1099INT.Summary.Box14`|`string`|`extract`|Box 14 extracted from Form 1099-INT.|0516273849|
|`Form1099INT.Summary.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-INT||
|`Form1099INT.Summary.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099INT.Summary.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-INT.|WA|
|`Form1099INT.Summary.StateTaxesWithheld.*.Box16`|`string`|`extract`|Box 16 extracted from Form 1099-INT.|123456789|
|`Form1099INT.Summary.StateTaxesWithheld.*.Box17`|`number`|`extract`|Box 17 extracted from Form 1099-INT.|123|
|`Form1099INT.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-INT.|false|
|`Form1099MISC`|`object`|`generate`|||
|`Form1099MISC.Summary`|`object`|`generate`|Summary of Form 1099-MISC.||
|`Form1099MISC.Summary.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box7`|`boolean`|`extract`|Box 7 extracted from Form 1099-MISC.|false|
|`Form1099MISC.Summary.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box14`|`number`|`extract`|Box 14 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.Box15`|`number`|`extract`|Box 15 extracted from Form 1099-MISC.|0|
|`Form1099MISC.Summary.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-MISC||
|`Form1099MISC.Summary.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099MISC.Summary.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-MISC.|123|
|`Form1099MISC.Summary.StateTaxesWithheld.*.Box17`|`string`|`extract`|Box 17 extracted from Form 1099-MISC.|12-3456789|
|`Form1099MISC.Summary.StateTaxesWithheld.*.Box18`|`number`|`extract`|Box 18 extracted from Form 1099-MISC.|0|
|`Form1099MISC.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-MISC.|false|
|`Form1099OID`|`object`|`generate`|||
|`Form1099OID.Summary`|`object`|`generate`|Summary of Form 1099-OID.||
|`Form1099OID.Summary.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-OID.|654321|
|`Form1099OID.Summary.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-OID.|123456|
|`Form1099OID.Summary.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-OID.|12345|
|`Form1099OID.Summary.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-OID.|6741|
|`Form1099OID.Summary.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-OID.|125|
|`Form1099OID.Summary.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-OID.|1.20|
|`Form1099OID.Summary.Box7`|`string`|`extract`|Box 7 extracted from Form 1099-OID.|NYSE MSFT COUPON 10% 1234|
|`Form1099OID.Summary.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-OID.|9875|
|`Form1099OID.Summary.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-OID.|951|
|`Form1099OID.Summary.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-OID.|123.56|
|`Form1099OID.Summary.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-OID.|987.20|
|`Form1099OID.Summary.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-OID||
|`Form1099OID.Summary.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099OID.Summary.StateTaxesWithheld.*.Box12`|`string`|`extract`|Box 12 extracted from Form 1099-OID.|WA|
|`Form1099OID.Summary.StateTaxesWithheld.*.Box13`|`string`|`extract`|Box 13 extracted from Form 1099-OID.|98-1234567|
|`Form1099OID.Summary.StateTaxesWithheld.*.Box14`|`number`|`extract`|Box 14 extracted from Form 1099-OID.|52123|
|`Form1099OID.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-OID.|false|
