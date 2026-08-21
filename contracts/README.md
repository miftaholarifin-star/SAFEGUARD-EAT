# Smart contract reference

`SafeguardEatQualityGate.sol` is a reference escrow contract that separates
funding, evidence-based evaluation, release, and refund. It is not deployed by
this repository.

Before any use with real funds, the design requires:

- an independent smart-contract security audit;
- an approved identity and access model;
- a trusted oracle or multisignature evidence process;
- legal review of procurement, payment, and dispute rules;
- network selection, key management, monitoring, and incident response;
- testnet verification followed by controlled acceptance testing.

The FastAPI application does not call this contract. It only returns a payment
recommendation for authorized human review.
