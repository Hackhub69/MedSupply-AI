# Hackathon demonstration guide

## Pitch
MedSupply AI helps a hospital network spot potential medicine shortages sooner and review stock-transfer opportunities using a shared inventory view.

## Three-minute demo
1. **Problem (20 seconds):** Medicine demand varies across facilities. A network-wide view can reveal a shortage at one hospital while another has surplus.
2. **Inventory monitor (40 seconds):** Open the dashboard. Show the shortage and expiry counts, search a medicine, and filter for shortages. Explain days of supply and the 28-day average.
3. **What-if (40 seconds):** Select Central Hospital / Amoxicillin, choose +50% demand, and run the simulation. Compare before and after coverage and the suggested donor quantity. The simulation does not change records.
4. **Transfer review (40 seconds):** Open a suggestion. Compare recipient and donor stock and daily use. Explain the 30-day donor reserve, batch checks, and human review. The review label exists only in the browser tab; no transfer is dispatched.
5. **Architecture and Db2 (40 seconds):** Describe the database tables and LangChain document retrieval. If configured and verified against Db2, show the Db2 connection evidence. Otherwise, clearly identify the local demo.

## Talking points
- **Impact:** earlier visibility into shortages and expiry risks is a hypothesis; clinical and financial impact have not been measured.
- **Design:** Flask reads inventory and demand, calculates risk and constrained transfer suggestions, and retrieves policy excerpts with LangChain.
- **Explainability:** each suggestion shows quantity, coverage, and reserve rules. The simulator shows the effect of a demand change.
- **Responsible deployment:** suggestions require pharmacist review. Data is synthetic. No orders or transfers are performed.
- **Next work:** validate on real datasets, model missing data and lead times, add batch-specific constraints and cold-chain logistics, use a validated forecasting model and Db2 vector search, and add identity controls and audit history.

## Submission materials
Capture screenshots of the overview, a simulation, and the review dialog. Record the walkthrough. Connect and validate Db2; fork the official repository, follow its template, open a PR, and submit the PR URL through the official form. These steps require the official links and a Db2 instance.
