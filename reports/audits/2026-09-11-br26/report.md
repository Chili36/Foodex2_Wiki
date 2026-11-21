# BR26/BR27: slutlig granskning och rättning

Datum: 2026-09-11. Wikiutgångspunkt: `aff6858`. Validatorutgångspunkt: `014b29465b22a09b96ca4956fdcca7a137593c42`.

## Slutsats

BR26 fick för stor betydelse i wikins kodningsflöde. Att en metod finns och har definierad varningsnivå gör den inte till en aktiv kontroll. Den granskade ICT-koden kör BR27 men har anropet till BR26 utkommenterat. Källan förklarar inte varför BR26 stängdes av.

Rättningen tar bort BR26 som obligatoriskt kodningskrav, inklusive krav på ordinalunderlag, avvisning och rutinmässig ”ej verifierat”-hantering. Historisk regeldefinition och skillnaden mot den egna validatorn finns kortfattat kvar på regelsidan. Bevara provets processinformation; välj inte bort en process för att klara en antagen BR26-konflikt.

## Validatorn

[Validator-PR #27](https://github.com/Chili36/automatic-couscous/pull/27) tar bort BR26-anropet ur den normala valideringen. Metoden finns kvar som referenskod, med korrekt explicit-F28-villkor och separata metodtester. Detta återaktiverar inte BR26 och skapar inget nytt konfigurationsläge.

BR27 fortsätter att köras och kräver olika icke-heltalsvärden inom samma heltalsfamilj, med en explicit process i just den familjen. Lika decimalvärden ensamma utlöser inte BR27. Den tidigare rotgruppsrättningen i [PR #24](https://github.com/Chili36/automatic-couscous/pull/24) mergades 2026-09-08; uppgiften att den väntade var fel.

PR #27 är föreslagen och inte driftsatt. Äldre validatorversioner kan fortfarande köra BR26 och ge de gamla BR27-utfallen.

## Källor

- [ICT-anropen, låst EFSA-commit](https://github.com/openefsa/catalogue-browser/blob/9a028ee0efe6a018e7f941ce0a4f7e6488b80e43/src/main/java/business_rules/TermRules.java#L1656-L1663): BR27 aktiv, BR26 utkommenterad.
- [BR27-metoden](https://github.com/openefsa/catalogue-browser/blob/9a028ee0efe6a018e7f941ce0a4f7e6488b80e43/src/main/java/business_rules/TermRules.java#L650-L780): olika decimalvärden och explicit process inom familjen.
- [Granskad äldre validator](https://github.com/Chili36/automatic-couscous/blob/014b29465b22a09b96ca4956fdcca7a137593c42/server/validators/business-rules-validator.js): aktiv BR26 och BR27 som räknar processer utan krav på olika värden.

## Verifiering

Validatorns `npm test` passerar: 18 nya metodtester, befintliga servicekontroller och sju katalogtester. Katalogtesterna kontrollerar både att normala resultat saknar BR26 och att den historiska metodens rotgruppsuppslag fortfarande kan testas separat.

| Katalogfall | Normal körning efter ändringen |
| --- | --- |
| `A00ZB#F28.A0C6N$F28.A07LN` | Varken BR26 eller BR27; lika decimalvärden |
| `A00ZB#F28.A0C6N$F28.A07KF` | BR27; olika decimalvärden inom samma familj |

Övriga varningar kan fortfarande förekomma för dessa koder; tabellen gäller endast BR26/BR27.

`reproduce.cjs` är en kompletterande historisk reproduktion av metodskillnaderna i validator-commit `014b294`, med syntetiska katalogvärden. Den visar vad den äldre koden gör, inte vad det uppdaterade standardflödet ska göra. EFSA-förväntningarna bygger på läsning av den låsta Java-koden, inte en körning av ICT. Kör skriptet med sökvägen till just den äldre validatorfilen.

Granskningen omfattar processreglernas policy, dokumentation, tester och index. Den är inte en fullständig omvalidering av alla FoodEx2-termer eller källdokument. Ingen validator har driftsatts som del av arbetet.

Slutkontroll av wikin: 179 tester godkända, Wiki Doctor med 0 fel. Den valfria externa länkkontrollen visar en befintlig HTTP 404 för README-länken till `Chili36/DMT`. Full omindexering med nya embeddingar är klar: 33 sidor, 267 textdelar, inga inaktuella eller saknade poster. Den lokala tjänsten har startats om och serverar policy `2026-09-11-v0.10`.
