# 🛒 Pi-Native Marketplace Architecture
### Amazon/Jumia Model · Pi Network Payment Rails

---

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PI MARKETPLACE PLATFORM                      │
│                                                                  │
│  [Seller Portal]  ──→  [Product Listings]  ──→  [Buyer App]     │
│        │                     │                       │          │
│        ↓                     ↓                       ↓          │
│  [Seller Wallet]     [Marketplace Engine]    [Buyer Wallet]      │
│        │                     │                       │          │
│        └──────────→  [Pi Payment Rails]  ←──────────┘          │
│                              │                                   │
│                    [Pi Blockchain / SDK]                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 👥 Core Actors

| Actor | Role | Pi Wallet |
|---|---|---|
| **Seller** | Lists products, fulfills orders | Receives Pi after settlement |
| **Buyer** | Browses, purchases, pays in Pi | Spends Pi, locked in escrow |
| **Marketplace** | Escrow agent, dispute handler, fee collector | Holds escrow + collects % fee |
| **Pi Network** | Payment infrastructure, identity (KYC) | Blockchain layer |

---

## 🔄 Full Order Lifecycle (Step-by-Step)

```
1. LISTING
   Seller → uploads product (title, price in π, images, stock)
   Platform → stores listing, converts π price to display currency

2. DISCOVERY
   Buyer → browses/searches catalog
   Platform → shows price in π + equivalent fiat estimate

3. CHECKOUT
   Buyer → clicks "Buy with Pi"
   Platform → generates PaymentID + order metadata

4. PAYMENT INITIATION
   Buyer's Pi App → opens Pi SDK payment dialog
   Platform → calls Pi.createPayment({amount, memo, metadata})

5. ESCROW LOCK 🔒
   Pi Network → deducts π from buyer wallet
   Funds held → in marketplace escrow address
   Platform → marks order as "PAYMENT_PENDING"

6. PAYMENT VERIFICATION ✅
   Platform backend → calls Pi.verifyPayment(paymentId)
   Pi API → confirms txn on blockchain
   Platform → marks order "CONFIRMED" → notifies seller

7. FULFILLMENT
   Seller → ships physical goods OR delivers digital goods
   Seller → marks order "SHIPPED" with tracking
   Buyer → confirms receipt OR auto-confirm after N days

8. SETTLEMENT 💸
   Platform → calls Pi.completePayment(paymentId)
   Escrow → released to seller wallet (minus platform fee %)
   Platform → marks order "COMPLETED"

9. DISPUTE WINDOW ⚠️
   If buyer disputes → funds held in escrow
   Marketplace mediates → releases to winner
```

---

## 🏛️ Architecture Components

### **Frontend Layer**
```
├── Buyer App (React Native / PWA)
│   ├── Product catalog + search
│   ├── Cart & checkout
│   └── Pi SDK integration (in-app browser)
│
└── Seller Portal (Web Dashboard)
    ├── Product management
    ├── Order management
    └── Earnings / payout dashboard
```

### **Backend Layer**
```
├── API Gateway
├── Marketplace Service
│   ├── Product/Inventory Service
│   ├── Order Management System (OMS)
│   └── User/KYC Service
│
├── Payment Service  ← CORE
│   ├── Pi SDK Server-side wrapper
│   ├── Escrow Manager
│   ├── Settlement Engine
│   └── Fee Calculator
│
└── Notification Service (Push, Email, SMS)
```

### **Pi Payment Integration Layer**
```
Pi Platform SDK
├── Pi.authenticate()      → verify buyer identity
├── Pi.createPayment()     → initiate payment + lock funds
├── Pi.verifyPayment()     → server-side blockchain confirm
├── Pi.completePayment()   → release from escrow to seller
└── Pi.cancelPayment()     → refund to buyer
```

---

## 💰 Payment Flow (Technical)

```javascript
// BUYER SIDE (Frontend)
const payment = await Pi.createPayment({
  amount: 12.5,           // π amount
  memo: "Order #ORD-8821",
  metadata: { orderId: "ORD-8821", sellerId: "seller_xyz" }
}, {
  onReadyForServerApproval: (paymentId) => {
    // Send paymentId to your backend for approval
    api.approvePayment(paymentId);
  },
  onReadyForServerCompletion: (paymentId, txid) => {
    // Tell backend to finalize + release to seller
    api.completePayment(paymentId, txid);
  },
  onCancel: (paymentId) => { api.cancelOrder(paymentId); },
  onError: (error) => { handleError(error); }
});

// SERVER SIDE (Backend)
async function approvePayment(paymentId) {
  const payment = await piClient.verifyPayment(paymentId);
  // Validate amount matches order total
  await db.orders.updateStatus(payment.metadata.orderId, "PAYMENT_LOCKED");
  await piClient.approvePayment(paymentId); // approve escrow lock
}

async function completePayment(paymentId, txid) {
  const payment = await piClient.verifyPayment(paymentId);
  // Blockchain confirmed — release to seller
  await settleToSeller(payment.metadata.sellerId, payment.amount);
  await piClient.completePayment(paymentId);
}
```

---

## 🧾 Fee & Settlement Model

```
Buyer pays:    12.50 π
─────────────────────────────────
Platform fee:   1.25 π  (10%)
Seller gets:   11.25 π
─────────────────────────────────
Settlement:    Instant after fulfillment confirm
               OR auto-release after 7 days
```

> **Note:** Platform fee structure can vary — flat fee, % of sale, or subscription for sellers (like Jumia's model).

---

## 🛡️ Trust & Safety Layer

| Concern | Solution |
|---|---|
| **Buyer fraud** | Pi KYC (Pi's identity layer), dispute window |
| **Seller fraud** | Seller verification, ratings, escrow delays |
| **Payment disputes** | Funds locked in escrow until resolution |
| **Double spend** | Pi blockchain confirmation before order proceeds |
| **Fake listings** | AI moderation + community flagging |

---

## 🗄️ Database Schema (Core Tables)

```sql
users         (id, pi_uid, kyc_status, role, wallet_address)
products      (id, seller_id, title, price_pi, category, stock)
orders        (id, buyer_id, seller_id, product_id, amount_pi,
               status, payment_id, txid, created_at)
payments      (id, order_id, pi_payment_id, txid, amount,
               fee_pi, status, escrow_released_at)
disputes      (id, order_id, raised_by, reason, status, resolution)
```

---

## 🌍 Why This Works for Pi Network

- ✅ **Pi's stated mission** = real-world utility for Pi holders
- ✅ **No speculation** — fixed prices in π, not trading π
- ✅ **KYC built-in** — Pi already does identity verification
- ✅ **Fits Open Mainnet** — Pi SDK supports real payments
- ✅ **Jumia market fit** — African/emerging market users already use Pi heavily
- ✅ **Escrow = trust** — solves the classic peer-to-peer commerce trust gap

---

## 🚀 MVP Feature Scope

```
Phase 1 — Core Marketplace
  ☐ Seller onboarding + product listings
  ☐ Pi SDK payment integration (escrow)
  ☐ Order management + buyer confirmation
  ☐ Settlement engine

Phase 2 — Trust & Scale
  ☐ Ratings & reviews
  ☐ Dispute resolution system
  ☐ Seller analytics dashboard
  ☐ Search & recommendation engine

Phase 3 — Advanced
  ☐ Digital goods delivery (instant settlement)
  ☐ Multi-seller cart checkout
  ☐ Subscription seller plans
  ☐ Mobile app (React Native)
```

---

> This is a **fully viable** product using Pi Network's own SDK — no exchange mechanics, no price speculation, just **commerce with Pi as currency**.
