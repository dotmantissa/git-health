import { CHAIN_ID, NETWORK_NAME } from '../constants';

function shortAddress(address) {
  if (!address) return '';
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export default function WalletBar({
  isConnected,
  address,
  chainId,
  wrongNetwork,
  onConnect,
  onDisconnect,
  onSwitch
}) {
  return (
    <header className="wallet-bar">
      <div className="wordmark">GitHealth</div>
      <div className="wallet-actions">
        {!isConnected ? (
          <button className="btn-connect" onClick={onConnect} type="button">
            Connect Wallet
          </button>
        ) : (
          <>
            <div className="wallet-pill">
              <span className="dot-online" />
              <span>{shortAddress(address)}</span>
            </div>
            <button className="btn-disconnect" onClick={onDisconnect} type="button">
              Disconnect
            </button>
            {!wrongNetwork && chainId === CHAIN_ID ? (
              <div className="network-pill">
                {NETWORK_NAME} · #{CHAIN_ID}
              </div>
            ) : (
              <div className="network-warning">
                <span>⚠ Wrong Network — Switch to GenLayer Studio</span>
                <button className="inline-switch" onClick={onSwitch} type="button">
                  Switch
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </header>
  );
}
