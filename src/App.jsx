import { useEffect, useMemo, useState } from 'react';
import { Contract, JsonRpcProvider } from 'ethers';
import WalletBar from './components/WalletBar';
import RepoInput from './components/RepoInput';
import ScoreGauge from './components/ScoreGauge';
import HistoryList from './components/HistoryList';
import { ABI, CHAIN_ID, CONTRACT_ADDRESS, RPC_URL } from './constants';
import { useWallet } from './hooks/useWallet';

function truncateError(message) {
  if (!message) return 'Unknown error';
  return message.length > 120 ? `${message.slice(0, 120)}...` : message;
}

function isValidGithubUrl(url) {
  return url.startsWith('https://github.com/');
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isTransientReadError(error) {
  const msg = String(error?.message || '').toLowerCase();
  return (
    msg.includes('missing revert data') ||
    msg.includes('action="call"') ||
    msg.includes('execution reverted')
  );
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
  const [loadingStep, setLoadingStep] = useState(0);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [history, setHistory] = useState([]);
  const [readProvider] = useState(() => new JsonRpcProvider(RPC_URL));

  useEffect(() => {
    if (!inlineError && !walletError) return undefined;
    const timer = setTimeout(() => {
      setInlineError('');
      clearError();
    }, 6000);
    return () => clearTimeout(timer);
  }, [inlineError, walletError, clearError]);

  useEffect(() => {
    if (!loading) return undefined;
    const interval = setInterval(() => {
      setLoadingStep((prev) => (prev + 1) % 3);
    }, 4000);
    return () => clearInterval(interval);
  }, [loading]);

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
    setLoadingStep(0);
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

  const resolveScoreAfterAnalyze = async (url) => {
    const maxAttempts = 45;
    const delayMs = 2000;
    const readContract = new Contract(CONTRACT_ADDRESS, ABI, readProvider);

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        const score = await readContract.get_score(url);
        return Number(score);
      } catch (error) {
        const isLastAttempt = attempt === maxAttempts;
        if (!isTransientReadError(error) || isLastAttempt) {
          throw error;
        }
        await sleep(delayMs);
      }
    }

    throw new Error('Timed out while finalizing score from chain state');
  };

  const handleAnalyze = async () => {
    setInlineError('');
    clearError();

    if (!validateInput()) return;
    if (gateError) {
      setInlineError(gateError);
      return;
    }

    try {
      setLoading(true);
      setLoadingStep(0);

      const contract = new Contract(CONTRACT_ADDRESS, ABI, signer);
      const tx = await contract.analyze_repo(repoUrl.trim());
      await tx.wait();
      const score = await resolveScoreAfterAnalyze(repoUrl.trim());

      const entry = {
        url: repoUrl.trim(),
        score,
        timestamp: new Date().toISOString()
      };
      pushHistory(entry);
    } catch (error) {
      if (error?.code === 4001) {
        setInlineError('Transaction rejected by user');
      } else if (
        String(error?.message || '').toLowerCase().includes('network') ||
        String(error?.message || '').toLowerCase().includes('failed to fetch')
      ) {
        setInlineError('RPC connection failed — is GenLayer Studio running?');
      } else {
        setInlineError(truncateError(error?.message));
      }
    } finally {
      setLoading(false);
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

    try {
      const contract = new Contract(CONTRACT_ADDRESS, ABI, readProvider);
      const score = await contract.get_score(repoUrl.trim());
      const entry = {
        url: repoUrl.trim(),
        score: Number(score),
        timestamp: new Date().toISOString()
      };
      pushHistory(entry);
    } catch (error) {
      if (
        String(error?.message || '').toLowerCase().includes('network') ||
        String(error?.message || '').toLowerCase().includes('failed to fetch')
      ) {
        setInlineError('RPC connection failed — is GenLayer Studio running?');
      } else {
        setInlineError(truncateError(error?.message));
      }
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
          loadingStep={loadingStep}
        />

        {activeError ? <p className="error-banner">{activeError}</p> : null}

        <ScoreGauge entry={selectedEntry} />

        <HistoryList history={history} onSelect={setSelectedEntry} />
      </main>
    </div>
  );
}
