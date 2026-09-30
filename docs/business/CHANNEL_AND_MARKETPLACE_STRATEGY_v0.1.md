# HUB_Optimus — Channel and Marketplace Strategy v0.1

**Status:** Owner decision recorded in issue `#1863`; repository ratification proposed  
**Research date:** 8 August 2026  
**Owner and final commercial authority:** Benjamin Gerrit Hoff

## 1. Decision

HUB_Optimus adopts a **hybrid channel architecture**:

1. **Microsoft Marketplace — primary software and enterprise private-offer rail.**
2. **Direct enterprise contracting — strategic transformations and contracts that
   cannot or should not fit a marketplace transaction.**
3. **AWS Marketplace — secondary multi-cloud and professional-services rail.**
4. **Approved Merchant of Record — standardized, low-touch digital subscriptions
   and smaller international transactions.**
5. **No single channel receives control, ownership, exclusivity, or the right to
   define HUB_Optimus prices.**

The marketplace is commercially valuable because it can simplify customer
procurement, billing, private offers, cloud-commitment consumption, channel sales,
and enterprise governance. It is not a substitute for product readiness,
security, financial-sector compliance, vendor due diligence, or HUB_Optimus's own
accounting and tax obligations.

## 2. Why Microsoft Marketplace is the primary channel

HUB_Optimus and LCDH-OS currently have strong Microsoft 365, Azure, Entra,
SharePoint, Outlook, Power Platform, Dataverse, and Microsoft Graph alignment.
Microsoft Marketplace therefore offers the closest initial customer and
technology fit.

Current official Microsoft documentation states that:

- the standard Marketplace service fee for a transactable offer is 3%;
- Microsoft bills the customer and pays 97% of the software license amount to the
  publisher in the standard example;
- negotiated private offers are available;
- eligible offers can contribute to a customer's Microsoft Azure Consumption
  Commitment (MACC);
- private marketplaces let enterprise customers govern which products can be
  purchased;
- multiparty private offers support software-company and channel-partner sales;
- IP co-sell eligibility requires an Azure-platformed, transactable offer and
  supporting technical and sales material.

Primary references:

- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/marketplace-commercial-transaction-capabilities-and-considerations
- https://learn.microsoft.com/en-us/marketplace/azure-consumption-commitment-benefit
- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/azure-consumption-commitment-enrollment
- https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/enable-marketplace-purchases
- https://learn.microsoft.com/en-us/partner-center/referrals/co-sell-requirements
- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/multiparty-private-offers-overview

### Commercial advantages

- The buyer can use an established Microsoft billing relationship.
- A private offer can carry negotiated pricing and terms for a specific customer.
- A MACC-eligible purchase can use budget the customer has already committed to
  Azure, reducing internal resistance to a new supplier.
- Microsoft can become a co-sell and channel ecosystem rather than merely a cloud
  provider.
- Enterprise buyers can apply Private Marketplace controls and procurement
  governance.
- The 3% fee is economically reasonable when it shortens procurement, collection,
  and vendor-onboarding friction.

### What Microsoft Marketplace does not do

A listing does not by itself:

- certify HUB_Optimus for banking or regulated financial services;
- satisfy DORA, GDPR, ISO, SOC, outsourcing, operational-resilience, model-risk,
  security, or local regulatory obligations;
- approve customer data use;
- replace the customer's vendor-risk assessment;
- remove the publisher's tax, accounting, corporate, sanctions, or legal duties;
- generate enterprise demand automatically;
- guarantee payment before Microsoft has collected from the customer.

## 3. Microsoft Marketplace implementation burden

A transactable SaaS offer is a product-integration project, not a simple profile
page.

Microsoft requires, among other items:

- Microsoft Entra ID authentication and SSO;
- a customer landing page;
- SaaS Fulfillment API integration;
- subscription activation, plan, quantity, suspension, reinstatement, renewal,
  and cancellation handling;
- a connection webhook available 24x7;
- tax and payout profiles in Partner Center;
- operating processes for failed, delayed, canceled, and modified subscriptions.

References:

- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/plan-saas-offer
- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/create-new-saas-offer-technical
- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/pc-saas-fulfillment-apis
- https://learn.microsoft.com/en-us/partner-center/account-settings/set-up-your-payout-account

Therefore Marketplace onboarding must be implemented as a governed HUB_Optimus
billing and entitlement adapter with tests, idempotency, audit, reconciliation,
security, and rollback.

## 4. Microsoft professional services

Microsoft currently allows professional services to be transacted through
private offers. These services are customer-specific and are not generally
visible as normal storefront lead-generating products.

References:

- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/plan-professional-service-offer
- https://learn.microsoft.com/en-us/partner-center/marketplace-offers/create-professional-service-offer

Use Microsoft professional-services private offers when the customer values
Microsoft billing and procurement integration. Do not expect the professional-
services listing itself to create demand.

## 5. AWS Marketplace as the secondary rail

AWS Marketplace is commercially attractive for:

- customers whose procurement and cloud commitment are AWS-centered;
- multi-cloud deployments;
- professional services;
- strategic private offers and renewals;
- financial-sector buyers with established AWS purchasing controls.

Current official AWS documentation states:

- public SaaS listing fee: 3%;
- private software offers: 3% below USD 1 million TCV, 2% from USD 1 million to
  below USD 10 million, and 1.5% at USD 10 million or above;
- private-offer renewals: 1.5%;
- professional-services private offers: 0.5% from June 2026.

References:

- https://docs.aws.amazon.com/marketplace/latest/userguide/listing-fees.html
- https://aws.amazon.com/about-aws/whats-new/2026/06/reduce-listing-fee-professional-services-aws-marketplace/

The 0.5% professional-services fee is particularly attractive for paid
diagnostics, pilots, implementation, and managed services when the buyer already
uses AWS Marketplace.

AWS remains secondary initially because the current HUB_Optimus/LCDH-OS stack is
more Microsoft-centered. It should not be ignored: financial institutions often
operate multi-cloud procurement and may prefer an existing AWS vendor route.

## 6. Merchant of Record

An approved Merchant of Record can handle end-customer payment collection,
transaction taxes, compliant digital invoices, fraud, chargebacks, refunds, and
customer billing support for eligible standardized software sales.

Public reference pricing on 8 August 2026:

- Paddle: 5% + USD 0.50 per checkout transaction;
- Lemon Squeezy: 5% + USD 0.50 per transaction;
- volume pricing may be negotiated.

References:

- https://www.paddle.com/pricing
- https://www.lemonsqueezy.com/pricing

Use a Merchant of Record for:

- standardized modules;
- lower-touch subscriptions;
- smaller international buyers;
- self-service digital products;
- transactions where global indirect-tax handling is worth the higher fee.

Do not make a Merchant of Record the default for multi-million-euro enterprise,
public-sector, OEM, regulated, or deeply negotiated agreements. At that scale,
private marketplace offers or direct enterprise contracts normally preserve more
control and economics.

## 7. Direct enterprise contracting

Direct B2B remains necessary for:

- strategic transformation;
- unusual public procurement;
- multi-cloud or on-premises structures;
- source-code escrow or exceptional rights;
- complex data-processing and regulated-outsourcing terms;
- projects whose milestone billing cannot fit the selected marketplace;
- customers that cannot buy the relevant offer through Marketplace.

Direct does not mean HUB_Optimus personally pursues customer accounting teams.
The customer supplies a complete procurement pack and one accounts-payable owner.
HUB_Optimus uses an external accountant, tax adviser, legal counsel, and finance
operations provider for its own non-transferable obligations.

## 8. Financial-sector strategy

Marketplace participation is strategically useful for the future financial and
economic sector because it can provide:

- procurement through an established hyperscaler relationship;
- private offers and negotiated commercial terms;
- cloud-commitment alignment;
- private-marketplace governance;
- a path toward co-sell and partner channels;
- consolidated billing and auditable procurement records;
- compatibility with customers' cloud vendor-management processes.

However, financial-sector readiness requires a separate trust program:

- reference architecture and data-flow documentation;
- tenant and environment isolation;
- encryption and key-management model;
- audit and immutable logs;
- incident, continuity, recovery, and exit plans;
- subcontractor and fourth-party register;
- DORA and operational-resilience mapping where applicable;
- GDPR, data-residency, retention, and deletion controls;
- secure development lifecycle and vulnerability management;
- model and AI governance;
- ISO 27001/SOC 2 or equivalent assurance roadmap;
- professional liability, cyber insurance, and regulated-contract support.

Microsoft for Financial Services provides compliance resources and dedicated
programs, but those resources do not certify a third-party product automatically.

References:

- https://learn.microsoft.com/en-us/industry/financial-services/fsi-overview
- https://learn.microsoft.com/en-us/industry/financial-services/compliance-fsi
- https://learn.microsoft.com/en-us/industry/financial-services/resources-evidence-fsi
- https://learn.microsoft.com/en-us/industry/financial-services/service-enablement-framework

## 9. Recommended launch sequence

### Stage 0 — Commercial readiness

- confirm contracting entity, tax adviser, payout account, bank, insurance, and
  invoicing architecture;
- register the commercial SKUs and rights matrix;
- define entitlement, tenant, usage-metering, invoice, and suspension events;
- prepare security, privacy, support, and financial-sector trust materials;
- open Microsoft Partner Center publisher and Marketplace profiles.

### Stage 1 — Microsoft listing and inbound qualification

- publish a `Contact me`/lead-generation listing first if immediate visibility is
  useful;
- expose no free bespoke deliverable;
- use `Request Institutional Access` as the call to action;
- build the transactable SaaS adapter in parallel.

Microsoft documentation states that the `Contact me` listing option has no SaaS
technical integration requirement, while transactable SaaS requires the full
Fulfillment API, landing-page, SSO, and webhook implementation.

### Stage 2 — Transactable Microsoft SaaS

Launch the minimum productized SKUs:

1. HUB_Optimus Core Business annual canon;
2. HUB_Optimus Enterprise private plan;
3. one application/module;
4. one standard connector bundle;
5. API Base annual commitment;
6. support tier.

Keep complex implementation and transformation separately scoped.

### Stage 3 — Private offers, MACC, and co-sell

- use private offers for negotiated enterprise transactions;
- achieve Azure-platform technical validation and IP co-sell readiness;
- seek MACC eligibility at offer level;
- prepare one-pager, pitch deck, reference architecture, customer evidence, and
  qualified pipeline;
- enable multiparty private offers when a channel partner adds funded commercial
  value.

### Stage 4 — AWS and Merchant of Record

- create an AWS professional-services offer for eligible private transactions;
- add AWS SaaS only when multi-cloud demand justifies the integration;
- use an approved Merchant of Record for standardized self-service products and
  smaller international transactions.

## 10. Channel decision rule

Use this order:

```text
Microsoft-aligned enterprise software/private offer
    → Microsoft Marketplace

AWS-centered professional service or multi-cloud buyer
    → AWS Marketplace

Standardized low-touch international subscription
    → approved Merchant of Record

Strategic, regulated, sovereign, unusual, or multi-million transformation
    → direct B2B or negotiated private marketplace offer
```

The customer may express a preferred procurement channel. The price is grossed
up so the required HUB_Optimus net amount is preserved. Channel convenience is a
customer benefit, not a discount funded by HUB_Optimus.
