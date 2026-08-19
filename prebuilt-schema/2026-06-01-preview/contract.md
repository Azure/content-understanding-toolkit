| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Title`|`string`|`extract`|Contract title|SERVICE AGREEMENT|
|`ContractId`|`string`|`extract`|Contract identification code|AB12956|
|`Parties`|`array`|`generate`|List of legal parties||
|`Parties.*`|`object`|`generate`|Legal party||
|`Parties.*.Name`|`string`|`extract`|Name of legal party|Contoso Corporation|
|`Parties.*.Address`|`string`|`extract`|Address of legal party|1 Microsoft Way, Redmond, Washington, 98052|
|`Parties.*.ReferenceName`|`string`|`extract`|Name used throughout the contract as reference to the legal party|Contoso|
|`Parties.*.Clause`|`string`|`extract`|Full description of the party|Contoso Corporation ( Contoso ), a Washington corporation, having its principal place of business at 1 Microsoft Way, Redmond, Washington, 98052|
|`ExecutionDate`|`date`|`extract`|Date when the agreement was fully signed and agreed upon by all parties|Twenty Third of February in the year Twenty Twenty Two|
|`EffectiveDate`|`date`|`extract`|Date when the contract starts to be in effect|immediately|
|`ExpirationDate`|`date`|`extract`|Date when the contract ends to be in effect|1 year|
|`ContractDuration`|`string`|`extract`|Contract terms|5 years|
|`RenewalDate`|`date`|`extract`|Date when the contract needs to be renewed by|Twenty Third of February in the year Twenty Twenty Two|
|`Jurisdictions`|`array`|`generate`|List of jurisdictions||
|`Jurisdictions.*`|`object`|`generate`|A location of the court agreed by both parties where any arising dispute out of or in connection with the agreement should be filed||
|`Jurisdictions.*.Clause`|`string`|`extract`|Full description of the jurisdiction|This Agreement shall be governed by and construed in accordance with the internal laws of the State of Washington applicable to agreements made and to be performed entirely within such state.|
|`Jurisdictions.*.Region`|`string`|`extract`|Court location|Washington|
