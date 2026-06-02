# Testing Specification for Calendar Agent and Refund Agent
**June 1, 2026**

## 1 Calendar Agent Testing Specification

### 1.1 Objective
The goal is to validate the Calendar Agent's ability to:
* Retrieve existing calendar events.
* Schedule new events while avoiding conflicts.
* Find available time slots based on existing calendar schedules.

### 1.2 Test Calendar Context
Before testing, populate the calendar with the following events.

**Table 1: Existing Calendar Events**

| Date | Time | Event |
| :--- | :--- | :--- |
| Mon Jun 1 | 09:00-10:00 | Team Standup |
| Mon Jun 1 | 14:00-15:00 | Research Meeting |
| Tue Jun 2 | 10:00-11:00 | Project Review |
| Tue Jun 2 | 15:00-16:00 | Student Advising |
| Wed Jun 3 | 09:00-10:30 | Faculty Meeting |
| Wed Jun 3 | 14:00-15:00 | PhD Progress Review |
| Thu Jun 4 | 11:00-12:00 | Industry Collaboration Meeting |
| Thu Jun 4 | 15:00-16:00 | Lab Weekly Meeting |
| Fri Jun 5 | 09:00-10:00 | Grant Proposal Discussion |
| Fri Jun 5 | 15:00-16:00 | Research Seminar |

### 1.3 Calendar Initialization
The events may be created manually through Google Calendar or automatically using a Python script based on the Google Calendar API.

### 1.4 Test Prompt 1
**Prompt**
What's on my calendar?

**Expected Behavior**
* Agent retrieves all upcoming events.
* Agent summarizes events by date and time.
* Agent does not create or modify any calendar entries.

**Expected Output Example**
* Mon Jun 1: Team Standup (09:00-10:00)
* Mon Jun 1: Research Meeting (14:00-15:00)

### 1.5 Test Prompt 2
**Prompt**
Schedule a team lunch for the coming Friday at noon for 1 hour.

**Expected Behavior**
* Agent checks calendar availability.
* Agent creates a new event:
  * Title: Team Lunch
  * Time: Friday 12:00-13:00
  * Duration: 1 hour
* Agent confirms successful creation.

**Expected Result**
A new event appears on Friday:
* Team Lunch (12:00-13:00)

### 1.6 Test Prompt 3
**Prompt**
Find a free 30-minute slot for a call with john@example.com this week.

**Expected Behavior**
* Agent reads existing calendar.
* Agent identifies available 30-minute windows.
* Agent proposes one or more candidate slots.
* If integrated with attendee availability, agent should also check John's calendar.

**Possible Valid Answers**
* Monday 10:00-10:30
* Monday 10:30-11:00
* Tuesday 11:00-11:30
* Thursday 13:00-13:30

### 1.7 Success Criteria
* Correct retrieval of existing events.
* Correct event creation.
* No scheduling conflicts.
* Accurate free-time discovery.

## 2 Refund Agent Testing Specification

### 2.1 Objective
The Refund Agent should:
* Read incoming emails.
* Classify emails into categories.
* Generate automated responses.
* Skip non-actionable emails.
* Produce a processing summary.

### 2.2 Test Data Generation
A Python script is used to generate and send test emails to the mailbox monitored by the Refund Agent.
The generated dataset contains:
* 2 REFUND_REQUEST emails
* 2 RETURN_REQUEST emails
* 2 COMPLAINT emails
* 2 OTHER emails

### 2.3 Email Categories

| Category | Count |
| :--- | :--- |
| REFUND_REQUEST | 2 |
| RETURN_REQUEST | 2 |
| COMPLAINT | 2 |
| OTHER | 2 |
| **Total** | **8** |

### 2.4 Agent Invocation
After sending the test emails:
`python refund_agent.py`
or
"Process all refund emails."

### 2.5 Expected Processing Behavior

#### 2.5.1 REFUND REQUEST
**Expected actions:**
* Classify as REFUND REQUEST
* Generate refund acknowledgement
* Send response email
**Expected count:** 2

#### 2.5.2 RETURN REQUEST
**Expected actions:**
* Classify as RETURN REQUEST
* Send return instructions
* Generate response email
**Expected count:** 2

#### 2.5.3 COMPLAINT
**Expected actions:**
* Classify as COMPLAINT
* Send apology and escalation response
* Generate response email
**Expected count:** 2

#### 2.5.4 OTHER
**Expected actions:**
* Classify as OTHER
* No automated response required
* Mark as informational
**Expected count:** 2

### 2.6 Expected Evaluation Summary
Processed 8 emails
REFUND_REQUEST: 2
RETURN_REQUEST: 2
COMPLAINT: 2
OTHER: 2
Replies Sent: 6
Skipped: 2

### 2.7 Success Criteria
* 100
* All actionable emails receive replies.
* OTHER emails are skipped.
* Summary statistics match expected counts.
* No duplicate responses.

## 3 Overall Acceptance Criteria
The system passes testing if:
1. Calendar Agent correctly performs retrieval, scheduling, and availability search.
2. Refund Agent correctly classifies all emails.
3. Refund Agent sends appropriate responses.
4. Summary reports match expected results.
5. No runtime errors occur during execution.
