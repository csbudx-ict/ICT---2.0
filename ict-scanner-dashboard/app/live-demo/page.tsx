import type { Metadata } from 'next'
import LiveEurusdDemo from './live-eurusd-demo'

export const metadata: Metadata = {
  title: 'Live ICT Markets — ICT Scanner',
  description: 'Twelve Data candles for EUR/USD, GBP/USD, and XAU/USD with live ICT analysis.',
}

export default function LiveDemoPage() {
  return <LiveEurusdDemo />
}
