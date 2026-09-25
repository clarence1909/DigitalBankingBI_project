# Banking glossary

The banking and analytics terms used in this project, in plain words, with where each one appears. KPI IDs (K01 to K22) refer to the [KPI dictionary](05_kpi_dictionary.md).

> **All data is synthetic.** Kelip Bank is fictional; the terms and the Malaysian context are real.

## Contents

- [Deposits and funding](#deposits-and-funding)
- [Lending and credit risk](#lending-and-credit-risk)
- [Payments and cards](#payments-and-cards)
- [Customers and growth](#customers-and-growth)
- [Malaysian context](#malaysian-context)
- [Analysis and reporting](#analysis-and-reporting)

## Deposits and funding

**CASA (current account and savings account).** Money customers keep in accounts they can use at any time. For a bank it is cheap funding: it pays a low rate, and balances are spread across many customers. At Kelip Bank, CASA means the Kelip Savings account.

**CASA ratio (K14).** CASA balances as a share of all deposits. A high ratio means cheaper, more stable funding. Kelip Bank plans for at least 80%.

**Fixed deposit (FD).** Money placed for a fixed term (6 or 12 months at Kelip Bank) at a fixed rate. It costs the bank more than CASA, but the bank knows how long it will have the money.

**Rollover.** When a fixed deposit matures and the customer places it again for another term, instead of taking the money out.

**FD retention at maturity (K16).** The share of matured fixed deposit money still with the bank 30 days later, whether rolled over or left in savings.

**Cost of funds (K15).** What the bank pays for its deposits, as an annual rate: interest paid on deposits divided by average deposits, annualised. Lower is better.

**Net interest income, NII (K22).** Interest earned on loans minus interest paid on deposits. For most banks it is the largest source of income.

**Net interest margin (NIM).** NII as a share of the assets that earn interest. Not a KPI here, but the reason the CASA ratio and cost of funds matter.

**Deposit promotion.** A higher rate for a limited time to attract deposits, such as Kelip Bank's Raya FD at 3.88%. The risk is that it mostly reprices money the bank already had, which is what finding 3 shows.

**New money.** Deposits brought in from other banks, as opposed to money moved from the customer's own savings at the same bank.

## Lending and credit risk

**Personal financing.** An unsecured personal loan. "Financing" is the usual word in Malaysia, where Islamic and conventional banking sit side by side.

**Principal.** The amount lent. **Outstanding principal** is what is still owed.

**Gross loans (K17).** The outstanding principal of all loans on the books, before any provision for losses.

**Instalment.** A regular monthly repayment of principal and interest.

**DPD (days past due).** How many days the oldest unpaid instalment is overdue. A loan paid on time is 0 DPD.

**Arrears bucket.** Loans grouped by DPD: current (0), 1 to 29, 30 to 59, 60 to 90, and 90+.

**PAR30, portfolio at risk (K19).** The share of gross loans 30 or more days past due. The standard early warning of credit trouble. Kelip Bank plans for at most 3.0%.

**Impaired loan and GIL ratio (K20).** A loan is impaired when the bank no longer expects to be repaid in full; in this project, more than 90 days past due. The gross impaired loans (GIL) ratio is impaired loans as a share of gross loans, and Bank Negara Malaysia publishes it for the whole banking system.

**MFRS 9 stages.** The accounting standard (Malaysia's version of IFRS 9) sorts loans into Stage 1 (performing), Stage 2 (credit risk has risen a lot; 30 DPD is the usual backstop) and Stage 3 (credit-impaired; 90 DPD). PAR30 and GIL roughly track Stages 2 and 3. Provisions for expected losses are out of scope here.

**Write-off.** Removing a loan the bank no longer expects to collect from the books.

**Vintage.** All loans paid out in the same month. Following each vintage month by month (a **vintage curve**) shows whether newer loans go bad faster than older ones at the same age, which a single PAR30 figure hides.

**Month on book (MOB).** How many months since a loan was paid out. Vintage curves use it as the x-axis.

**Early delinquency at month 6 (K21).** The share of a vintage that has been 30+ days past due at least once by month 6 on book. It gives an early read on a vintage's quality.

**Roll rate.** Of the loans in one arrears bucket this month, the share that move to a worse bucket next month. **Cure rate** is the share that go back to current.

**Credit policy.** The rules for who gets a loan and on what terms: which risk grades, the maximum debt service ratio, pricing. Kelip Bank had three (v1, v2, v3), and finding 4 compares them.

**Risk grade.** A score band (A best to D worst) from the credit assessment, which sets the price and whether the loan is approved.

**DSR (debt service ratio).** A borrower's monthly debt repayments as a share of their monthly income. A higher maximum DSR lets more people borrow, and more of them struggle to repay.

**Thin file.** An applicant with little credit history, so the bank knows less about the risk.

**Risk appetite.** How much risk the bank has decided to accept. In this project: no more than 5% of a vintage 30+ days past due by month 6.

## Payments and cards

**DuitNow.** Malaysia's instant transfer service, run by PayNet: money moves between banks in seconds using a phone number, MyKad number or account number. **DuitNow QR** is the national QR code for paying in shops.

**Debit card.** A card that spends money directly from the savings account.

**Card activation (K10).** The customer switching on a newly issued card in the app. Finding 1 shows that customers who activate within 30 days are far more likely to stay active.

**Authorisation.** The card processor's real-time approval or decline of a card payment.

**Settlement.** When an approved payment is actually paid and posted to the account, usually a day or two after authorisation. Card spend here is counted at settlement (K11).

**Response code.** The processor's code for an authorisation's outcome: 00 approved, 51 insufficient funds, 55 wrong PIN, 59 suspected fraud.

**Approval rate (K12).** Approved authorisations as a share of all attempts.

**MCC (merchant category code).** A four-digit code for the type of shop, such as 5411 for groceries. Categories are taken from it rather than the free-text merchant label.

**Reversal.** An authorisation cancelled after approval, for example when a purchase is refunded before it settles.

**Interchange.** The fee the merchant's bank pays the card-issuing bank on each card payment. It is why card spend earns the bank money; not modelled here.

## Customers and growth

**eKYC (electronic know your customer).** Checking a customer's identity remotely, in the app, instead of in a branch. At Kelip Bank: scan the MyKad, then pass a selfie liveness check.

**MyKad.** The Malaysian national identity card.

**Liveness check.** A selfie test that the applicant is a live person, not a photo or video of one. It is the step where most applicants drop out (finding 2).

**Onboarding funnel.** The steps from starting sign-up to an open account, and the share of applicants who reach each one (K03, K04).

**CAC, customer acquisition cost (K05).** Marketing spend divided by new customers. This project adds a second view: the cost per customer still active three months later, which is what the spend is really buying.

**Cohort.** Customers who opened their account in the same month.

**Active customer (K07, K08).** A customer who made at least one transaction themselves in the month: a transfer, bill payment, card purchase or fixed deposit placement. Interest and incoming salary do not count, because they happen without the customer doing anything.

**Month-3 active rate (K06).** The share of a cohort still active in their third month after opening; the project's measure of whether new customers stay.

**Churn.** Customers who stop using the bank, whether or not they close the account.

**Dormant customer.** A customer with an open account who has made no transactions of their own for months (six, in the segments analysis).

## Malaysian context

**Bank Negara Malaysia (BNM).** Malaysia's central bank and banking regulator.

**Digital bank.** A bank licensed under BNM's digital bank framework, which serves customers only through apps and online, with no branches. BNM awarded the first five licences in 2022.

**OPR (Overnight Policy Rate).** BNM's policy interest rate. When it falls, banks usually cut their deposit and lending rates. BNM cut it from 3.00% to 2.75% on 9 July 2025, and Kelip Bank cut its savings and FD rates from 1 August 2025.

**Ringgit (RM) and sen.** Malaysia's currency; 100 sen make one ringgit. The reconciliations tie "to the sen", meaning exactly.

**Hari Raya.** Hari Raya Aidilfitri, the festival at the end of Ramadan, a common time for bank promotions. Kelip Bank's FD promotion ran over Raya 2025.

**PDPA.** The Personal Data Protection Act 2010, which a real bank's reporting would have to comply with.

## Analysis and reporting

**KPI (key performance indicator).** A measure the bank tracks against a target, with a named owner.

**Scorecard.** The six KPIs with a monthly plan, each given a status each month.

**RAG status.** Red, amber, green. Here: On plan (▲), Watch (●) and Off plan (▼), always shown with the icon and word as well as the colour.

**Amber band.** How far a KPI can be worse than plan before it turns red, set per KPI as a share of plan.

**Plan.** The monthly target from the financial plan. Kelip Bank's financial year is the calendar year.

**Reconciliation.** Proving two systems agree. Here: that each account's month-end balance equals the sum of its ledger postings, and that every settled card payment matches a ledger posting.

**Star schema.** A warehouse design with fact tables (what happened: postings, authorisations, balances) surrounded by dimension tables (who and what: customers, accounts, products, dates). See the [ER diagram](er_diagram.md).

**Grain.** What one row of a table stands for, such as one posting, or one account at one month end.

**A/B test.** Randomly showing two versions (here, the control and guided eKYC flows) to comparable groups and comparing the outcome.

**Sample-ratio mismatch (SRM).** When the groups in an A/B test are not the sizes the design intended, which means the randomisation may be broken and the result cannot be trusted. It is checked before anything else.

**Guardrail metric.** A measure that must not get worse while the primary metric improves; here, the share of new accounts flagged for fraud.

**Credible interval.** In a Bayesian test, the range the true effect lies in with a stated probability, such as 95%.

**k-means.** A method that groups customers with similar behaviour into k segments. **Silhouette score** measures how well separated the groups are, and is used to choose k.
