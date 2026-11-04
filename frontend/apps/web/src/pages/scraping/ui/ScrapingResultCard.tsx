import type { ScrapingResult } from "../../../shared/api";

const LOG_HINT = "아래 실행 로그에서 오류를 확인하세요.";

type CardView = {
	title: string;
	description: string;
	border: string;
	titleColor: string;
};

/**
 * 서버가 준 상태를 카드의 문구와 색으로 옮긴다. 상태를 다시 판단하지 않는다.
 * @param result - 실행 결과
 * @returns 카드에 그릴 문구와 Tailwind 클래스
 */
function toCardView({ status, saved }: ScrapingResult): CardView {
	if (status === "failed") {
		return {
			title: "❌ 실패",
			description: `저장한 공고가 없습니다. ${LOG_HINT}`,
			border: "border-l-red-600",
			titleColor: "text-red-700",
		};
	}
	if (status === "partial") {
		return {
			title: "⚠️ 부분 실패",
			description: `일부 공고를 저장하지 못했습니다. ${LOG_HINT}`,
			border: "border-l-amber-600",
			titleColor: "text-amber-700",
		};
	}
	const success = {
		border: "border-l-green-600",
		titleColor: "text-green-700",
	};
	return saved === 0
		? {
				...success,
				title: "✅ 완료 · 신규 0건",
				description: "새 공고가 없습니다. 정상 결과입니다.",
			}
		: {
				...success,
				title: "✅ 완료",
				description: `새 공고 ${saved.toLocaleString()}건을 모두 저장했습니다.`,
			};
}

/**
 * 스크래핑이 끝난 뒤 상태와 건수를 보여 주는 카드.
 * @param props.result - 서버가 보낸 실행 결과
 * @returns 결과 카드
 */
export function ScrapingResultCard({ result }: { result: ScrapingResult }) {
	const view = toCardView(result);
	const counts = [
		{ label: "수집", value: result.collected, color: "text-slate-800" },
		{ label: "저장", value: result.saved, color: "text-slate-800" },
		{ label: "실패", value: result.failed, color: "text-red-600" },
		{ label: "건너뜀", value: result.skipped, color: "text-slate-800" },
	];

	return (
		<div
			className={`rounded-lg border border-l-4 border-slate-200 bg-white p-4 shadow-sm ${view.border}`}
		>
			<div className={`font-semibold ${view.titleColor}`}>{view.title}</div>
			<div className="mt-0.5 text-sm text-slate-600">
				{result.job} · {view.description}
			</div>
			<div className="mt-3 grid grid-cols-4 gap-2">
				{counts.map(({ label, value, color }) => (
					<div key={label} className="rounded-md bg-slate-50 p-2 text-center">
						<div className={`text-xl font-bold ${color}`}>
							{value.toLocaleString()}
						</div>
						<div className="text-xs text-slate-500">{label}</div>
					</div>
				))}
			</div>
		</div>
	);
}
