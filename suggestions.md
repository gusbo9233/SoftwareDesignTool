Architecture Decision Record (ADR).
This is the clearest omission. The app has architecture diagrams, but no structured way to record why a design decision was made, what alternatives were considered, and what tradeoffs were accepted. That leaves diagrams without decision history.

Which frameworks and programming laguages etc that should be used.


Non-functional requirements.
The current requirement type appears to lump everything together. I would split or extend it to explicitly support performance, security, reliability, scalability, privacy, and compliance requirements. Those usually drive architecture more than functional requirements do.

Risk register.
There is a risk section inside project_plan, but that is weaker than a first-class document type. Risks usually evolve independently and need ownership, status, mitigation progress, and review cadence.

System context / domain model.
You have ER and UML diagrams, but no dedicated document that defines bounded contexts, major entities, domain language, business rules, and external systems in prose.

Acceptance test / test specification.
You have test_plan, but that is still fairly high-level. A separate document for executable acceptance criteria, traceability to requirements, and scenario coverage would help.

Collection of external resources that should be used e.g. external apis that should be used. 

Collection of research documents. These should be freetext. 

Clear connection between requirements and test cases. 