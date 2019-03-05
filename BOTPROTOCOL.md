# Communication protocol of bots which wish to use the currency management protocol

Some bots will want to provide services that are dependent on this bot to provide payment.
To do this, they must convey requests to this bot in a particular way.

Here is what the interaction will look like from the user's perspective:

```
user> awesomebot buy 10
awesomebot> Communicating with the finance service...
awesomebot> money transaction awesomebot Q2FuJ3QgYmVsaWV2ZSB5b3UnZCB0YWtlIHRoZSB0aW1lIHRvIHJlYWQgdGhpcyEK
money> awesomebot transaction_answer SSBtZWFuLCBpdCBpc24ndCBsaWtlIEkgd291bGQgcHV0IGFjdHVhbCBkYXRhIGluIGhlcmUsIHJpZ2h0Pwo=
awesomebot> Purchase complete. 10 FOOBARs have been added to your inventory.
```

When your bot wishes to perform a transaction, it sends a message with the contents `money transaction {peer's name} {data}`.
After that, this bot will respond with `{peer's callsign} transaction_answer {data}`. 
The rest of this document shall describe what the `{data}` fields are.

## General
For the remainder of the document, "peer" is understood to mean the bot that wishes to communicate with this one, and "bot" is the finance management bot.

The communication is encrypted with RSA.
Before being sent, each side's message is first encrypted with the other's public key, then encoded in Base64.
Exchange of public keys is done in a method selected by the server administrator.
Because pure-RSA encryption is used, the peer must generate a keypair of such a length that all messages which the peer is intending to send fit that length.
The bot's key's length will be sufficient to fit all of the expected messages from the bot.

A peer must be registered in the bot's database.
If the `{peer's name}` is not found, the request will not be considered.
The reason for this is that the `{peer's name}` allows the bot to find the peer's public key, as well as the `{peer's callsign}` to bring the data to the peer's attention.

## Methods
`TODO`