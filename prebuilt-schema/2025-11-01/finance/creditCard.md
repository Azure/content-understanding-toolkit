**Analyzer ID:** `prebuilt-creditCard`

**Description:** Credit card statements.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`CardNumber`|`string`|`extract`|A unique identifier for the card|4275 0000 0000 0000|
|`IssuingBank`|`string`|`extract`|The name of the bank that issued the card|Woodgrove Bank|
|`PaymentNetwork`|`string`|`extract`|The payment network that processes the card transactions|VISA|
|`CardholderName`|`string`|`extract`|The name of the person who owns the card|JOHN SMITH|
|`CardholderCompanyName`|`string`|`extract`|The name of the company that the card is associated with|CONTOSO SOFTWARE|
|`ValidFromDate`|`string`|`extract`|Valid from date|01/16|
|`ExpirationDate`|`string`|`extract`|Expiration date|01/28|
|`CardVerificationValue`|`string`|`extract`|Card verification value (CVV)|764|
|`CustomerServicePhoneNumbers`|`array`|`generate`|||
|`CustomerServicePhoneNumbers.*`|`string`|`extract`|A phone number that can be used to contact the customer service of the issuing bank or the card network|+1 200-345-6789|
