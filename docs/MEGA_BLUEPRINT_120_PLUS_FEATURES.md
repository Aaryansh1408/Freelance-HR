# Career Crox CRM - Mega Blueprint (120+ Features)

This file is included inside the project so the entire build context survives across chats, devices, and the usual human tendency to lose track of their own product scope.

## 1. Recruitment Core
1. Candidate timeline
2. One-click status flow
3. Auto follow-up engine
4. Duplicate candidate detector
5. Recruiter ownership lock
6. Resume upload tracker
7. Document availability flag
8. Candidate source tracking
9. Candidate blacklisting
10. Engagement score

## 2. Notes, Feedback, and Visibility
11. Public notes with author + designation + timestamp
12. Private notes per user
13. Manager visibility into all private notes
14. Last 5 notes quick view
15. Expand all note history
16. Note-based notifications
17. Note audit log
18. Pinned notes
19. Follow-up note templates
20. Tagging in notes

## 3. Dialer and Calling
21. Call outcome popup
22. Dialer queue
23. Talktime analytics
24. Connected call count
25. Best hour heatmap
26. Callback suggestion engine
27. Auto next call
28. Call script helper
29. Call recording link field
30. Hourly recruiter scoreboard

## 4. Interview Control
31. Interview kanban
32. Today / tomorrow / week calendar views
33. Interview confirmation tracker
34. Reschedule tracker
35. Attendance tracker
36. Interview feedback form
37. Interview slot suggestions
38. Round history
39. Panel assignment
40. Missed interview alerts

## 5. JD Centre
41. Highest payout sorting
42. JD aging tracker
43. JD difficulty score
44. JD ranking by closure speed
45. JD ranking by retention
46. JD notes
47. JD location / shift / salary details
48. Recommended JD match
49. JD status dashboard
50. JD owner assignment

## 6. Tasks and Productivity
51. Task create
52. Task assign
53. Reminder time
54. Popup reminders
55. Open / pending / closed views
56. Daily target tracker
57. Productivity score
58. Break monitoring
59. Idle recruiter tracker
60. Activity summary

## 7. Team and Admin Control
61. Role-based access
62. Admin / manager / TL / recruiter roles
63. User directory
64. Manager dashboards
65. Force logout design placeholder
66. Recruiter code mapping
67. Audit log
68. Ownership reassign
69. Access visibility map
70. Team-wise control panels

## 8. Communication
71. Internal chat
72. Chat groups (planned)
73. Notification center
74. Bulk WhatsApp templates
75. Single-send WhatsApp templates
76. Email templates
77. Scheduled notifications
78. Unread count badges
79. TL update alerts
80. Client confirmation reminders

## 9. Reports and Analytics
81. Daily report
82. Weekly report
83. Monthly report
84. Funnel analytics
85. Lead to join conversion
86. Source performance
87. Location analytics
88. Recruiter efficiency
89. TL-wise performance
90. Manager summary cards

## 10. Business and Payout
91. Payout eligibility tracker
92. Invoice readiness tracker
93. Client confirmation tracker
94. Recruiter earning summary
95. Team earning summary
96. Dispute tracker
97. Target vs achieved
98. Reward schemes
99. Milestone trips
100. Payout days visibility

## 11. UX / UI / Theming
101. 10 themes
102. 3 readable dark themes
103. Premium font
104. Animated bounce states
105. Big cards
106. Desktop-first layout
107. Sidebar navigation
108. Theme selector box
109. Notifications page
110. Chat page

## 12. Extra Modules
111. Meeting room preview
112. Learning hub preview
113. Social post scheduler preview
114. Wallet & rewards preview
115. Payout tracker preview
116. Reports preview
117. Preview page
118. Cross-chat context file
119. Full architecture notes
120. Folder structure documentation

## 13. Future AI / Automation
121. AI resume parsing
122. AI candidate matching
123. AI call summary
124. AI follow-up suggestions
125. AI duplicate confidence score
126. Smart interview scheduling
127. Auto payout reminders
128. Lead health score
129. Retention risk score
130. Auto daily executive summary


## Architecture
- Stack: Flask + SQLite + Jinja templates + plain HTML/CSS/JS
- Deployment: GitHub + Render
- Data seed: built-in seed + sample workbook in sample_data/
- Free-only tooling: no paid APIs required for running this demo

## Database Schema Summary
- users(username, full_name, designation, role, team, manager_username, password)
- jds(code, title, location, experience_required, payout, payout_days, status)
- candidates(code, full_name, phone, location, experience, status, recruiter_username, tl_username, jd_code, qualification, created_at)
- submissions(candidate_code, jd_code, recruiter_username, status, submitted_at)
- interviews(candidate_code, jd_code, stage, scheduled_at, status)
- tasks(title, description, assigned_to, priority, status, due_at)
- notes(candidate_code, username, note_type, body, created_at)
- notifications(username, candidate_code, title, message, is_read, created_at)
- messages(sender_username, recipient_username, body, created_at)
