import type { AnalysisResult } from '../types/analysis';

export const demoAnalysis: AnalysisResult = {
  analysis_id: 'demo-001',
  status: 'completed',
  created_at: '2025-06-15T14:30:00Z',
  summary: {
    property_address: '742 Evergreen Terrace, Apt 3B, Austin, TX 78701',
    landlord_name: 'Greenfield Property Management LLC',
    tenant_name: 'Sample Tenant',
    lease_start: '2025-08-01',
    lease_end: '2026-07-31',
    monthly_rent: 2150,
    security_deposit: 4300,
    lease_type: 'fixed',
  },
  clauses: [
    {
      id: 'c1',
      category: 'Entry & Access',
      title: 'Unrestricted landlord entry',
      original_text:
        'Landlord or their agents may enter the premises at any time for inspection, maintenance, or any purpose deemed necessary.',
      risk_level: 'critical',
      risk_explanation:
        'This clause gives the landlord unlimited access without notice. Texas Property Code §92.0081 requires landlords to provide reasonable notice before entry except in emergencies.',
      recommendation:
        "Negotiate to add: 'Landlord shall provide at least 24 hours written notice before entry, except in cases of emergency threatening life or property.'",
      section_reference: 'Section 7.1',
    },
    {
      id: 'c2',
      category: 'Lease Termination',
      title: 'Automatic renewal with 90-day cancellation window',
      original_text:
        'This lease shall automatically renew for successive one-year terms unless either party provides written notice of non-renewal at least 90 days prior to the expiration date.',
      risk_level: 'critical',
      risk_explanation:
        '90-day notice requirement is unusually long. If you miss the deadline by even one day, you are locked in for another full year. Most leases require only 30-60 days notice.',
      recommendation:
        'Negotiate down to a 30-day notice period, or at minimum request that the landlord send a reminder email 120 days before the deadline.',
      section_reference: 'Section 2.3',
    },
    {
      id: 'c3',
      category: 'Security Deposit',
      title: 'Vague deposit deduction terms',
      original_text:
        "Tenant shall pay a security deposit equal to two months' rent. Deposit may be applied to any damages, cleaning, or other charges as determined by Landlord in their sole discretion.",
      risk_level: 'high',
      risk_explanation:
        "The phrase 'sole discretion' gives the landlord unchecked power to make deductions without documentation. Combined with a 2x rent deposit ($4,300), your financial exposure is significant.",
      recommendation:
        "Request itemized deduction requirement with photographic evidence, and add: 'Deposit shall be returned within 30 days of lease termination per TX Property Code §92.103.'",
      section_reference: 'Section 3.2',
    },
    {
      id: 'c4',
      category: 'Maintenance',
      title: 'Tenant responsible for all repairs under $500',
      original_text:
        'Tenant shall be responsible for all repairs and maintenance costs under $500 per occurrence, including plumbing, electrical, and appliance repairs.',
      risk_level: 'high',
      risk_explanation:
        'This shifts a significant maintenance burden to you. Plumbing and electrical issues are typically landlord responsibilities under Texas law. Multiple $499 repairs could cost thousands over a year.',
      recommendation:
        "Counter with: Tenant responsible for repairs under $100 caused solely by tenant negligence. All plumbing, electrical, HVAC, and appliance repairs remain landlord's responsibility.",
      section_reference: 'Section 6.1',
    },
    {
      id: 'c5',
      category: 'Rent',
      title: 'Uncapped rent increase on renewal',
      original_text:
        'Upon renewal, Landlord may adjust monthly rent at their discretion. Tenant will be notified of new rent amount 30 days prior to renewal date.',
      risk_level: 'high',
      risk_explanation:
        'No cap on rent increases means the landlord could raise rent by any amount on renewal. Combined with the 90-day auto-renewal trap, you could get locked into a dramatically higher rate.',
      recommendation:
        "Negotiate a cap: 'Rent increases shall not exceed 5% per renewal term or the annual CPI increase, whichever is lower.'",
      section_reference: 'Section 3.4',
    },
    {
      id: 'c6',
      category: 'Liability',
      title: 'Overbroad liability waiver',
      original_text:
        'Tenant agrees to hold Landlord harmless from any and all claims, damages, or injuries occurring on the premises, regardless of cause.',
      risk_level: 'high',
      risk_explanation:
        "This waiver could release the landlord from liability even for their own negligence — for example, failing to fix a broken stair that causes injury. Courts often void such clauses, but it creates uncertainty.",
      recommendation:
        "Narrow the waiver: 'Tenant holds Landlord harmless only for damages caused solely by Tenant's negligence.' Landlord retains liability for structural defects and code violations.",
      section_reference: 'Section 9.2',
    },
    {
      id: 'c7',
      category: 'Pets',
      title: 'Non-refundable pet fee plus monthly pet rent',
      original_text:
        'Pets are permitted with prior written approval. A non-refundable pet fee of $500 and monthly pet rent of $75 shall apply per approved pet.',
      risk_level: 'medium',
      risk_explanation:
        '$500 non-refundable fee plus $75/month ($900/year) is above market rate in Austin. Non-refundable fees cannot be used to cover actual damage — they are pure landlord profit regardless of outcome.',
      recommendation:
        'Negotiate the non-refundable fee down to $250, or convert to a refundable pet deposit that only covers documented actual damage.',
      section_reference: 'Section 5.4',
    },
    {
      id: 'c8',
      category: 'Subletting',
      title: 'Absolute subletting prohibition',
      original_text:
        'Tenant shall not sublet, assign, or transfer this lease or any interest therein without express written consent of Landlord, which may be withheld for any reason.',
      risk_level: 'medium',
      risk_explanation:
        "Complete prohibition with 'withheld for any reason' gives you zero flexibility if your circumstances change (job relocation, family emergency). You'd be stuck paying rent on a place you can't use.",
      recommendation:
        "Change to: 'Consent to subletting shall not be unreasonably withheld. Landlord shall respond to subletting requests within 14 business days.'",
      section_reference: 'Section 8.1',
    },
    {
      id: 'c9',
      category: 'Utilities',
      title: 'Standard utility responsibilities',
      original_text:
        'Tenant shall be responsible for electricity, gas, water, internet, and trash collection. Landlord shall be responsible for sewer and common area maintenance.',
      risk_level: 'low',
      risk_explanation:
        'This is a standard utility split. All tenant-responsible utilities are individually metered, which is preferable to shared or estimated billing.',
      recommendation: 'No changes needed. This is a fair and transparent arrangement.',
      section_reference: 'Section 4.1',
    },
    {
      id: 'c10',
      category: 'Parking',
      title: 'One covered parking space included',
      original_text:
        'Tenant shall be assigned one covered parking space at no additional charge. Additional spaces may be rented at $75/month subject to availability.',
      risk_level: 'low',
      risk_explanation:
        'One free covered parking space is a good inclusion for Austin. The optional additional space at $75/month is at market rate.',
      recommendation:
        'Request that your specific assigned space number be written into the lease so it cannot be changed without notice.',
      section_reference: 'Section 5.2',
    },
  ],
  key_dates: [
    { event: 'Lease start date', date: '2025-08-01', notice_required: null },
    {
      event: 'Non-renewal notice deadline',
      date: '2026-05-03',
      notice_required: '90 days written notice required — mark this date now',
    },
    { event: 'Lease end date', date: '2026-07-31', notice_required: null },
    {
      event: 'Security deposit return deadline',
      date: '2026-08-30',
      notice_required: 'Landlord must return within 30 days per TX Property Code §92.103',
    },
  ],
  financial_summary: {
    total_monthly_cost: 2225,
    total_move_in_cost: 7075,
    annual_cost: 26700,
    penalties: [
      { type: 'Late rent fee', amount: 150, condition: 'Rent not received by 5th of month' },
      {
        type: 'Early termination penalty',
        amount: '3 months rent ($6,450)',
        condition: 'Breaking lease before end date',
      },
      { type: 'Returned check fee', amount: 50, condition: 'Per occurrence' },
    ],
  },
  risk_score: {
    overall: 42,
    breakdown: {
      financial_risk: 35,
      termination_risk: 28,
      maintenance_risk: 55,
      legal_risk: 48,
    },
  },
  missing_clauses: [
    'No mold disclosure or remediation clause',
    'No explicit provision for lease assignment in case of tenant death or incapacity',
    'No cap on annual rent increases upon renewal',
    'No clause addressing property damage from natural disasters or force majeure',
    "No renter's insurance requirement or waiver",
  ],
  red_flags: [
    'Landlord reserves unrestricted right to enter without notice — violates TX Property Code §92.0081',
    "Security deposit is 2x monthly rent with 'sole discretion' deduction terms — high clawback risk",
    'Automatic renewal requires 90-day cancellation notice — very easy to miss, locks you in for another year',
    "'Hold harmless' clause attempts to waive landlord liability even for their own negligence",
  ],
};
