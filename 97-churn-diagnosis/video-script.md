<!-- PROVN Challenge 97. Target 850 to 1050 words, 5.5 to 7 minutes at 150 wpm. Five sections. -->
<!-- 1. Opening -->
Fieldly's monthly churn rose from 2.1 percent to 3.4 percent over six months. That is a 62 percent increase. The board wants an answer Thursday, and Maya has five days to deliver it.

Here is the two sentence finding I built the rest of the work around. The spike comes almost entirely from small business Basic plan customers who activate only one feature and churn at 51.8 percent. Fix the first 30 days of onboarding so those accounts adopt at least two features, and most of the 62 percent goes with it.

<!-- 2. Analysis walkthrough -->
Let me walk through how I got there, because the path was not the most visible cut of the data.

Plan tier was the first signal. Basic churns at 27.7 percent. Enterprise churns at 5.6 percent. Chi square passes at p under 0.0001, so this is real and not noise. Company size tells the same story from a different angle. One to ten employee accounts churn at 29.2 percent. Fifty one to two hundred employee accounts churn at 6.2 percent. Both cuts point at the same population, small businesses on Basic.

Then I looked at feature adoption depth, and this is where the picture sharpened. Customers using zero features churn at 12 percent. Customers using one feature churn at 52 percent. Customers using two features drop back to 12 percent. Customers using three features churn at 3 percent. The curve is not monotonic. It spikes at one feature and falls away on either side. That non monotonic shape is the whole story.

Zero feature accounts are mostly new signups not activated yet, plus annual contracts that are nowhere near renewal. They are not at risk yet. Single feature accounts are different. They tried the product, they set up scheduling, they never connected dispatch or invoicing, and a year later they leave. That is the activation cliff. Two features is the threshold where the product starts being load bearing in their workflow. Three features and they are stuck to it.

Support tickets confirm the pattern. Bug tickets carry 34.7 percent churn. Onboarding tickets carry 29.7 percent churn. Churned customers open 4.46 tickets on average against 1.70 for retained customers, and they wait 6.17 days for resolution against 2.25 days. The customers who need help most are sitting in the longest queues, and they are the same population that never made it past one feature.

The fourth cut is cohort. The Q4 2024 signup cohort is 130 accounts, the largest in the dataset, churning at 26.9 percent. The weighted expected rate based on plan and size mix is 17.6 percent. That leaves a residual of plus 9.3 percentage points that demographics alone do not explain. Fisher exact comes back at p equals 0.0033. The cohort is additive to the demographic story, not a restatement of it. Q4 2024 also skews 56.9 percent Basic plan against 36.8 percent across the full base, so the cohort effect and the plan effect compound. Median time to churn is 12.4 months, which means the Q4 signups are cascading through their first renewal window right now. That is the mechanical reason this quarter looks worse than last quarter.

One methodology note. The 3.4 percent monthly rate is computed against an active customer denominator over a six month window, not lifetime accounts. I called that out in the document so the rate is reproducible.

<!-- 3. Stakeholder brief -->
The board brief, Section B, is 190 words. I built it to be read cold by a non technical reader. The first two sentences carry the finding. Sixty two percent rise concentrated in small Basic customers using one feature, churning at 52 percent against under 3 percent for full feature users. No chi square values, no p values, no Fisher tests. One paragraph on the mechanism, one paragraph on the recommended action. The technical appendix sits behind it for anyone who wants to verify. Maya can read this brief in under a minute and answer follow ups from memory.

<!-- 4. Mandatory AI question -->
Now the AI question. Claude's first plan led with industry segmentation. Pest Control versus HVAC versus Plumbing. It is the most visible cut of the data and it would have produced a clean vertical narrative for the board. I almost let it stand because it looked tidy.

Before I did, I ran a chi square on industry. P equals 0.47. There is no signal there. Industry differences fall inside random variation for a sample this size. I told Claude to drop the industry framing entirely and rebuild around plan tier and feature adoption depth, which both pass at p under 0.001. Industry got demoted to a null result in the appendix.

If I had taken the first plan at face value, Maya would be walking into Thursday recommending HVAC specific interventions, the activation cliff would still be losing customers in the background, and the next quarter's churn number would be worse, not better. The lesson is that AI gives you the most narratively satisfying cut of the data first. You have to test whether the satisfying cut is the true cut.

<!-- 5. Reflection -->
On limitations. The 3.4 percent rate is constrained by a static signup and churn snapshot. With a true event log, session level data, I could test the activation cliff hypothesis directly. I could measure exactly when single feature users drop off and whether there is a window where a triggered onboarding nudge would pull them across the two feature threshold. That would change the recommendation from a 30 day onboarding redesign to a behavior triggered intervention, which is cheaper to ship and easier to measure.

The other gap is contract term. I would segment annual versus monthly accounts if that field existed in the data. It does not, and that is a real blind spot. Annual contracts mask churn intent for up to twelve months, so the population I am counting as retained today includes some unknown fraction that has already mentally churned and is just running out the clock.
