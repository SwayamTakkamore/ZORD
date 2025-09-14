# Crypto Compliance Copilot - Web Dashboard

A Next.js web dashboard for compliance officers to monitor cryptocurrency transactions, override decisions, and anchor transaction states to the blockchain.

## Features

- **Real-time Transaction Monitoring**: Live updates of transaction status with automatic refresh
- **Manual Override System**: Compliance officers can override automatic decisions with audit trails
- **Blockchain Anchoring**: Batch anchor transaction states to Polygon blockchain for immutable records
- **Risk Assessment Display**: Visual risk scores and status indicators
- **Explorer Integration**: Direct links to blockchain explorers for transaction verification

## Quick Start

### Prerequisites

- Node.js 18.17.0 or later
- Backend API server running (from Module 4)

### Installation

```bash
# Navigate to web dashboard directory
cd web-dashboard

# Install dependencies
npm install --no-bin-links

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Default Login Credentials

```
Username: admin
Password: admin
```

## Configuration

The application uses environment variables for configuration:

### Environment Variables

Create a `.env.local` file:

```env
# Backend API Configuration
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_EXPLORER_BASE_URL=https://polygonscan.com

# Authentication Configuration
NEXT_PUBLIC_JWT_SECRET=your-secret-key-here
NEXT_PUBLIC_AUTH_ENABLED=false

# Development Configuration
NODE_ENV=development
```

## Architecture

### Pages
- `/` - Login page with demo credentials
- `/dashboard` - Main compliance dashboard

### Components
- `TransactionTable` - Real-time transaction monitoring table
- `OverrideModal` - Manual override interface for compliance officers
- `AnchorModal` - Blockchain anchoring interface

### API Integration
- Real-time data fetching with SWR
- Automatic retry and error handling
- JWT-based authentication (mock for MVP)

## API Endpoints Used

The dashboard integrates with these backend endpoints:

```
GET  /api/v1/transactions     - Fetch all transactions
POST /api/v1/transactions/override - Override transaction status
POST /api/v1/anchor          - Anchor transactions to blockchain
GET  /api/v1/anchor/status   - Check anchor status
GET  /health                 - Health check
```

## Features in Detail

### Transaction Monitoring
- Live table with real-time updates (5-second refresh)
- Sortable columns (timestamp, hash, amount, risk score, status)
- Risk score color coding (green: <40%, blue: 40-60%, yellow: 60-80%, red: 80%+)
- Status badges (pending, confirmed, flagged, blocked)
- Anchor status tracking

### Manual Override
- Override automatic decisions with reason logging
- Support for confirming or blocking transactions
- Audit trail for compliance requirements
- Real-time status updates

### Blockchain Anchoring
- Batch selection of transactions for anchoring
- Merkle root generation and blockchain submission
- Explorer links for verification
- Anchor status tracking and display

### Responsive Design
- Mobile-friendly interface
- Tailwind CSS for consistent styling
- Dark mode support (future enhancement)

## Development

### Available Scripts

```bash
npm run dev        # Start development server
npm run build      # Build for production
npm run start      # Start production server
npm run lint       # Run ESLint
npm run type-check # Run TypeScript checks
```

### Project Structure

```
web-dashboard/
├── pages/
│   ├── _app.tsx           # App layout and global styles
│   ├── index.tsx          # Login page
│   └── dashboard.tsx      # Main dashboard
├── components/
│   ├── TransactionTable.tsx  # Transaction monitoring table
│   ├── OverrideModal.tsx     # Manual override interface
│   └── AnchorModal.tsx       # Blockchain anchoring interface
├── lib/
│   └── api.ts             # API client and types
├── styles/
│   └── globals.css        # Global styles and Tailwind
└── public/               # Static assets
```

### Technology Stack

- **Next.js 14.0.0** - React framework with SSR/SSG
- **TypeScript** - Type safety and developer experience
- **Tailwind CSS** - Utility-first CSS framework
- **SWR** - Data fetching with caching and revalidation
- **Custom Design System** - Compliance-focused color palette

## Integration with Module 4

This dashboard integrates with the Module 4 backend services:

1. **Polygon Anchor Service** - For blockchain anchoring operations
2. **FastAPI Backend** - For transaction data and override operations
3. **Smart Contract** - For on-chain anchor verification

## Security Features

- JWT-based authentication (mock for MVP)
- CORS protection via Next.js configuration
- Input validation and sanitization
- Audit logging for compliance actions

## Deployment

For production deployment:

1. Build the application: `npm run build`
2. Start the production server: `npm run start`
3. Configure environment variables for production
4. Set up reverse proxy (nginx) if needed
5. Enable HTTPS for security

## Troubleshooting

### Common Issues

1. **Permission errors during npm install**
   ```bash
   npm install --no-bin-links
   ```

2. **Backend connection issues**
   - Verify `NEXT_PUBLIC_BACKEND_URL` in `.env.local`
   - Ensure backend server is running on correct port

3. **TypeScript errors**
   ```bash
   npm run type-check
   ```

4. **Styling issues**
   - Ensure Tailwind CSS is properly configured
   - Check `postcss.config.js` and `tailwind.config.js`

## Future Enhancements

- Dark mode support
- Advanced filtering and search
- Export functionality for audit reports
- Real-time notifications
- Multi-language support
- Advanced analytics dashboard

## License

This project is part of the Crypto Compliance Copilot MVP for the Yellow Network Hackathon 2025.
