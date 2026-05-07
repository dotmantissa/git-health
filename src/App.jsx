import { useEffect, useMemo, useState } from 'react';
import WalletBar from './components/WalletBar';
import RepoInput from './components/RepoInput';
import ScoreGauge from './components/ScoreGauge';
import HistoryList from './components/HistoryList';
import { CHAIN_ID } from './constants';
import { useWallet } from './hooks/useWallet';
import { analyzeRepo, getCachedScore } from './lib/genLayerClient';

function truncateError(message) {
  if (!message) return 'Unknown error';
  return message.length > 120 ? `${message.slice(0, 120)}...` : message;
}

function isValidGithubUrl(url) {
  return url.startsWith('https://github.com/');
}

export default function App() {
  const {
    provider,
    signer,
    address,
    isConnected,
    wrongNetwork,
    chainId,
    walletError,
    connect,
    disconnect,
    switchToGenLayer,
    clearError
  } = useWallet();

  const [repoUrl, setRepoUrl] = useState('');
  const [validationError, setValidationError] = useState('');
  const [inlineError, setInlineError] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!inlineError && !walletError) return undefined;
    const timer = setTimeout(() => {
      setInlineError('');
      clearError();
    }, 6000);
    return () => clearTimeout(timer);
  }, [inlineError, walletError, clearError]);

  const gateError = useMemo(() => {
    if (!isConnected) return 'Connect your wallet before interacting with the contract.';
    if (chainId !== CHAIN_ID) return 'Wrong network. Switch to GenLayer Studio to continue.';
    return '';
  }, [isConnected, chainId]);

  const resetAppState = () => {
    setRepoUrl('');
    setValidationError('');
    setInlineError('');
    setLoading(false);
    setStatusMessage(null);
    setSelectedEntry(null);
    setHistory([]);
  };

  const handleDisconnect = () => {
    disconnect();
    resetAppState();
  };

  const validateInput = () => {
    if (!isValidGithubUrl(repoUrl.trim())) {
      setValidationError('Must be a valid github.com URL');
      return false;
    }
    setValidationError('');
    return true;
  };

  const pushHistory = (entry) => {
    setHistory((prev) => [entry, ...prev]);
    setSelectedEntry(entry);
  };

  const handleAnalyze = async () => {
    setInlineError('');
    clearError();

    if (!validateInput()) return;
    if (gateError) {
      setInlineError(gateError);
      return;
    }
    if (!signer || !provider || !address) {
      setInlineError('Connect your wallet before interacting with the contract.');
      return;
    }

    try {
      setLoading(true);
      setStatusMessage('Submitting transaction…');

      const score = await analyzeRepo(address, repoUrl.trim(), setStatusMessage);

      const entry = {
        url: repoUrl.trim(),
        score,
        timestamp: new Date().toISOString()
      };
      pushHistory(entry);
    } catch (error) {
      if (error?.code === 4001 || error?.code === 'ACTION_REJECTED') {
        setInlineError('Transaction rejected.');
      } else {
        setInlineError(truncateError(error?.message || 'Transaction failed.'));
      }
    } finally {
      setLoading(false);
      setStatusMessage(null);
    }
  };

  const handleGetCached = async () => {
    setInlineError('');
    clearError();

    if (!validateInput()) return;
    if (gateError) {
      setInlineError(gateError);
      return;
    }
    if (!address) {
      setInlineError('Connect your wallet before interacting with the contract.');
      return;
    }

    try {
      setLoading(true);
      setStatusMessage('Reading result…');
      const score = await getCachedScore(address, repoUrl.trim());
      const entry = {
        url: repoUrl.trim(),
        score,
        timestamp: new Date().toISOString()
      };
      pushHistory(entry);
    } catch (error) {
      setInlineError(truncateError(error?.message || 'Read failed.'));
    } finally {
      setLoading(false);
      setStatusMessage(null);
    }
  };

  const activeError = inlineError || walletError;

  return (
    <div className="app-shell">
      <WalletBar
        isConnected={isConnected}
        address={address}
        chainId={chainId}
        wrongNetwork={wrongNetwork}
        onConnect={connect}
        onDisconnect={handleDisconnect}
        onSwitch={switchToGenLayer}
      />

      <hr className="divider" />

      <main className="main-column">
        <RepoInput
          repoUrl={repoUrl}
          onChange={(value) => {
            setRepoUrl(value);
            setValidationError('');
            setInlineError('');
            clearError();
          }}
          onAnalyze={handleAnalyze}
          onGetCached={handleGetCached}
          loading={loading}
          validationError={validationError}
          statusMessage={statusMessage}
        />

        {activeError ? <p className="error-banner">{activeError}</p> : null}

        <ScoreGauge entry={selectedEntry} />

        <HistoryList history={history} onSelect={setSelectedEntry} />
      </main>
    </div>
  );
}
