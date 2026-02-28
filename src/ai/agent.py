"""
AI Collection Agent - Intelligent billing assistant powered by OpenAI.

This agent provides:
1. Payment Risk Analysis - Predict likelihood of late payments
2. Collection Message Generation - Personalized reminders
3. Conversational Assistant - Answer questions about payments
4. Executive Summaries - AI-generated reports with insights
"""

import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

from openai import AsyncOpenAI

# Keywords related to school billing management
ALLOWED_TOPICS = {
    # Spanish keywords
    "pago",
    "pagos",
    "factura",
    "facturas",
    "deuda",
    "deudas",
    "saldo",
    "saldos",
    "cobro",
    "cobranza",
    "mensualidad",
    "cuota",
    "cuotas",
    "matrícula",
    "matricula",
    "estudiante",
    "estudiantes",
    "alumno",
    "alumnos",
    "padre",
    "padres",
    "apoderado",
    "escuela",
    "colegio",
    "instituto",
    "pensión",
    "pension",
    "mora",
    "morosidad",
    "vencido",
    "vencida",
    "pendiente",
    "pendientes",
    "abono",
    "abonos",
    "recibo",
    "estado de cuenta",
    "recordatorio",
    "notificación",
    "debe",
    "deben",
    "adeuda",
    "pagar",
    "cobrar",
    "facturar",
    "total",
    "monto",
    "importe",
    # English keywords (in case)
    "payment",
    "invoice",
    "debt",
    "balance",
    "student",
    "school",
    "billing",
    "fee",
    # Common variations
    "cunto",
    "cuanto",
    "cuando",
    "reportes",
    "reporte",
    "informe",
}

# Phrases that indicate off-topic questions
OFF_TOPIC_PATTERNS = [
    r"chiste",
    r"broma",
    r"clima",
    r"tiempo",
    r"cocina",
    r"receta",
    r"película",
    r"pelicula",
    r"música",
    r"musica",
    r"juego",
    r"jugar",
    r"historia de",
    r"quién (fue|es|era)",
    r"quien (fue|es|era)",
    r"capital de",
    r"presidente",
    r"futbol",
    r"fútbol",
    r"deportes",
]

from src.config import settings
from src.ai.schemas import (
    RiskLevel,
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    RiskFactor,
    CollectionMessageRequest,
    CollectionMessageResponse,
    AssistantRequest,
    AssistantResponse,
    ExecutiveSummaryRequest,
    ExecutiveSummaryResponse,
    TrendInsight,
    SchoolMetrics,
)


class CollectionAgent:
    """
    AI-powered collection agent for school billing management.

    Uses OpenAI API to provide intelligent insights and automation
    for payment collection processes.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the agent with OpenAI API key."""
        self.api_key = api_key or settings.openai_api_key
        self.client = None
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # or "gpt-3.5-turbo" for lower cost

    def _is_available(self) -> bool:
        """Check if AI agent is available (API key configured)."""
        return self.client is not None

    def _is_on_topic(self, question: str) -> Tuple[bool, str]:
        """
        Check if the question is related to school billing management.

        Returns:
            Tuple of (is_valid, reason)
        """
        question_lower = question.lower()

        # Check for off-topic patterns first
        for pattern in OFF_TOPIC_PATTERNS:
            if re.search(pattern, question_lower):
                return False, "La pregunta no está relacionada con gestión escolar o pagos."

        # Check if any allowed topic keyword is present
        words = re.findall(r"\w+", question_lower)
        for word in words:
            if word in ALLOWED_TOPICS:
                return True, ""

        # Check for common question patterns about the system
        system_patterns = [
            r"(cómo|como) (funciona|usar|uso)",
            r"(qué|que) (puedo|puede)",
            r"ayuda",
            r"hola",  # Greetings are OK
            r"gracias",
        ]
        for pattern in system_patterns:
            if re.search(pattern, question_lower):
                return True, ""

        # If question is very short (likely a greeting or simple query), allow it
        if len(words) <= 3:
            return True, ""

        # Default: reject if no billing-related keywords found
        return (
            False,
            "Por favor, realiza preguntas relacionadas con pagos, facturas, estudiantes o gestión escolar.",
        )

    async def analyze_payment_risk(self, request: RiskAnalysisRequest) -> RiskAnalysisResponse:
        """
        Analyze payment risk for a student based on their history.

        Uses AI to identify patterns and predict payment behavior.
        """
        if not self._is_available():
            return self._fallback_risk_analysis(request)

        # Build context for OpenAI
        payment_history_text = "\n".join(
            [
                f"- Invoice {p.invoice_id}: ${p.amount}, due {p.due_date}, "
                f"{'paid on ' + str(p.paid_date) if p.paid_date else 'UNPAID'}, "
                f"{p.days_late} days late, status: {p.status}"
                for p in request.payment_history[-10:]  # Last 10 payments
            ]
        )

        prompt = f"""Analiza el riesgo de pago para este estudiante y proporciona una evaluación.
IMPORTANTE: Toda la respuesta debe estar en ESPAÑOL.

INFORMACIÓN DEL ESTUDIANTE:
- Nombre: {request.student_name}
- Escuela: {request.school_name}
- Inscrito desde: {request.enrolled_since or 'Desconocido'}
- Total facturado: ${request.total_invoiced}
- Total pagado: ${request.total_paid}
- Total pendiente: ${request.total_pending}
- Total vencido: ${request.total_overdue}

HISTORIAL DE PAGOS (más recientes):
{payment_history_text if payment_history_text else 'Sin historial de pagos disponible'}

Proporciona tu análisis en el siguiente formato JSON (TODO EN ESPAÑOL):
{{
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "risk_score": <0-100>,
    "risk_factors": [
        {{"factor": "nombre del factor EN ESPAÑOL", "impact": "LOW|MEDIUM|HIGH", "description": "explicación EN ESPAÑOL"}}
    ],
    "recommendations": ["recomendación 1 EN ESPAÑOL", "recomendación 2 EN ESPAÑOL"],
    "predicted_payment_probability": <0.0-1.0>,
    "suggested_action": "acción específica a tomar EN ESPAÑOL",
    "analysis_summary": "resumen de 2-3 oraciones EN ESPAÑOL"
}}

Responde SOLO con el JSON, sin texto adicional."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            return RiskAnalysisResponse(
                student_id=request.student_id,
                risk_level=RiskLevel(result["risk_level"]),
                risk_score=result["risk_score"],
                risk_factors=[RiskFactor(**rf) for rf in result["risk_factors"]],
                recommendations=result["recommendations"],
                predicted_payment_probability=result["predicted_payment_probability"],
                suggested_action=result["suggested_action"],
                analysis_summary=result["analysis_summary"],
            )
        except Exception:
            # Fallback to rule-based analysis
            return self._fallback_risk_analysis(request)

    def _fallback_risk_analysis(self, request: RiskAnalysisRequest) -> RiskAnalysisResponse:
        """Fallback rule-based risk analysis when AI is not available."""
        # Calculate risk score based on simple rules
        risk_score = 0
        risk_factors = []

        # Factor 1: Overdue amount
        if request.total_overdue > 0:
            overdue_ratio = (
                float(request.total_overdue / request.total_invoiced)
                if request.total_invoiced > 0
                else 0
            )
            if overdue_ratio > 0.5:
                risk_score += 40
                risk_factors.append(
                    RiskFactor(
                        factor="Alto monto vencido",
                        impact="HIGH",
                        description="Más del 50% del total facturado está vencido",
                    )
                )
            elif overdue_ratio > 0.2:
                risk_score += 25
                risk_factors.append(
                    RiskFactor(
                        factor="Monto vencido significativo",
                        impact="MEDIUM",
                        description="Entre 20-50% del total está vencido",
                    )
                )
            else:
                risk_score += 10
                risk_factors.append(
                    RiskFactor(
                        factor="Monto vencido menor",
                        impact="LOW",
                        description="Menos del 20% está vencido",
                    )
                )

        # Factor 2: Payment history patterns
        late_payments = sum(1 for p in request.payment_history if p.days_late > 0)
        if len(request.payment_history) > 0:
            late_ratio = late_payments / len(request.payment_history)
            if late_ratio > 0.5:
                risk_score += 30
                risk_factors.append(
                    RiskFactor(
                        factor="Historial de pagos tardíos",
                        impact="HIGH",
                        description="Más del 50% de pagos fueron tardíos",
                    )
                )
            elif late_ratio > 0.2:
                risk_score += 15
                risk_factors.append(
                    RiskFactor(
                        factor="Algunos pagos tardíos",
                        impact="MEDIUM",
                        description="Entre 20-50% de pagos fueron tardíos",
                    )
                )

        # Factor 3: Pending amount ratio
        if request.total_invoiced > 0:
            pending_ratio = float(request.total_pending / request.total_invoiced)
            if pending_ratio > 0.7:
                risk_score += 20
                risk_factors.append(
                    RiskFactor(
                        factor="Alto porcentaje pendiente",
                        impact="HIGH",
                        description="Más del 70% del total está pendiente de pago",
                    )
                )

        # Determine risk level
        if risk_score >= 70:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 50:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 30:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Generate recommendations
        recommendations = []
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            recommendations.extend(
                [
                    "Contactar inmediatamente al responsable de pago",
                    "Considerar plan de pagos",
                    "Revisar historial de comunicaciones previas",
                ]
            )
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend(
                [
                    "Enviar recordatorio de pago",
                    "Ofrecer opciones de pago flexibles",
                ]
            )
        else:
            recommendations.append("Mantener comunicación regular")

        # Predicted probability (inverse of risk)
        predicted_prob = max(0.1, 1 - (risk_score / 100))

        return RiskAnalysisResponse(
            student_id=request.student_id,
            risk_level=risk_level,
            risk_score=min(100, risk_score),
            risk_factors=risk_factors,
            recommendations=recommendations,
            predicted_payment_probability=predicted_prob,
            suggested_action=recommendations[0] if recommendations else "Monitorear cuenta",
            analysis_summary=f"El estudiante {request.student_name} presenta un nivel de riesgo {risk_level.value}. "
            f"Se identificaron {len(risk_factors)} factores de riesgo. "
            f"Probabilidad estimada de pago en 30 días: {predicted_prob * 100:.0f}%.",
        )

    async def generate_collection_message(
        self, request: CollectionMessageRequest
    ) -> CollectionMessageResponse:
        """
        Generate a personalized collection message.

        Creates appropriate messaging based on tone, channel, and context.
        """
        if not self._is_available():
            return self._fallback_collection_message(request)

        tone_instructions = {
            "FRIENDLY": "amigable y cordial, como un recordatorio entre amigos",
            "FORMAL": "profesional y formal, manteniendo respeto",
            "URGENT": "urgente pero respetuoso, enfatizando la importancia",
            "FINAL_NOTICE": "serio y directo, indicando que es un aviso final antes de acciones adicionales",
        }

        channel_instructions = {
            "EMAIL": "un correo electrónico con asunto y cuerpo completo",
            "SMS": "un mensaje SMS corto (máximo 160 caracteres)",
            "WHATSAPP": "un mensaje de WhatsApp conversacional pero profesional",
        }

        prompt = f"""Genera un mensaje de cobranza en español con las siguientes características:

INFORMACIÓN:
- Estudiante: {request.student_name}
- Padre/Responsable: {request.parent_name or 'Estimado padre de familia'}
- Escuela: {request.school_name}
- Monto pendiente: ${request.pending_amount}
- Monto vencido: ${request.overdue_amount}
- Días de atraso: {request.days_overdue}
- Facturas pendientes: {request.invoices_pending}

ESTILO:
- Tono: {tone_instructions[request.tone.value]}
- Canal: {channel_instructions[request.channel.value]}
- Incluir llamado a acción de pago: {request.include_payment_link}
{f'- Contexto adicional: {request.custom_context}' if request.custom_context else ''}

Responde en formato JSON:
{{
    "subject": "asunto del correo (solo para EMAIL, null para otros)",
    "message": "el mensaje completo",
    "call_to_action": "frase específica de llamado a acción"
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            return CollectionMessageResponse(
                subject=result.get("subject"),
                message=result["message"],
                tone_used=request.tone,
                channel=request.channel,
                call_to_action=result["call_to_action"],
            )
        except Exception:
            return self._fallback_collection_message(request)

    def _fallback_collection_message(
        self, request: CollectionMessageRequest
    ) -> CollectionMessageResponse:
        """Fallback message generation when AI is not available."""
        parent_name = request.parent_name or "Estimado padre de familia"

        if request.tone.value == "FRIENDLY":
            if request.channel.value == "SMS":
                message = (
                    f"Hola! Recordatorio de {request.school_name}: "
                    f"Tienes ${request.pending_amount} pendiente. "
                    f"Gracias por tu pronto pago!"
                )
            else:
                message = f"""Estimado/a {parent_name},

Esperamos que se encuentre bien. Le escribimos de {request.school_name} para recordarle amablemente que tiene un saldo pendiente de ${request.pending_amount} correspondiente a {request.invoices_pending} factura(s).

Agradecemos su pronto pago para mantener al día la cuenta de {request.student_name}.

Saludos cordiales,
{request.school_name}"""

        elif request.tone.value == "URGENT":
            message = f"""Estimado/a {parent_name},

AVISO URGENTE: La cuenta de {request.student_name} presenta un saldo vencido de ${request.overdue_amount} con {request.days_overdue} días de atraso.

Es importante regularizar esta situación a la brevedad. El monto total pendiente es ${request.pending_amount}.

Por favor, comuníquese con nosotros para resolver esta situación.

Atentamente,
Administración - {request.school_name}"""

        elif request.tone.value == "FINAL_NOTICE":
            message = f"""AVISO FINAL

Estimado/a {parent_name},

A pesar de nuestros intentos previos de comunicación, la cuenta de {request.student_name} continúa con un saldo vencido de ${request.overdue_amount}.

Este es un aviso final antes de proceder con las acciones correspondientes según nuestro reglamento.

Monto total pendiente: ${request.pending_amount}
Días de atraso: {request.days_overdue}

Solicitamos su inmediata atención a este asunto.

Administración
{request.school_name}"""

        else:  # FORMAL
            message = f"""Estimado/a {parent_name},

Por medio de la presente, le informamos que la cuenta del estudiante {request.student_name} presenta un saldo pendiente de ${request.pending_amount}.

Le solicitamos amablemente realizar el pago correspondiente a la brevedad posible.

Quedamos a su disposición para cualquier consulta.

Atentamente,
Departamento de Cobranza
{request.school_name}"""

        subject = None
        if request.channel.value == "EMAIL":
            if request.tone.value == "FINAL_NOTICE":
                subject = f"AVISO FINAL - Cuenta pendiente de {request.student_name}"
            elif request.tone.value == "URGENT":
                subject = f"URGENTE: Saldo vencido - {request.student_name}"
            else:
                subject = f"Recordatorio de pago - {request.school_name}"

        return CollectionMessageResponse(
            subject=subject,
            message=message,
            tone_used=request.tone,
            channel=request.channel,
            call_to_action=(
                "Realizar pago ahora"
                if request.include_payment_link
                else "Contactar administración"
            ),
        )

    async def answer_question(self, request: AssistantRequest) -> AssistantResponse:
        """
        Answer questions about payments and accounts.

        Acts as a conversational assistant for billing inquiries.
        """
        # Validate that the question is on-topic
        is_valid, rejection_reason = self._is_on_topic(request.question)
        if not is_valid:
            return AssistantResponse(
                answer=rejection_reason + "\n\nPuedo ayudarte con:\n"
                "- Consultas sobre saldos y pagos\n"
                "- Estado de cuenta de estudiantes\n"
                "- Facturas pendientes y vencidas\n"
                "- Procesos de cobranza\n"
                "- Reportes financieros",
                suggested_actions=["Consultar saldo", "Ver facturas pendientes"],
                related_topics=["Pagos", "Facturación", "Cobranza"],
                confidence=1.0,
                requires_human_followup=False,
            )

        if not self._is_available():
            return self._fallback_assistant(request)

        # Build conversation history
        messages = [
            {
                "role": "system",
                "content": """Eres un asistente virtual especializado en gestión de cobranza escolar para Mattilda.

IMPORTANTE: El usuario es un ADMINISTRADOR del sistema con acceso COMPLETO a todos los datos.
Puedes y DEBES proporcionar información detallada incluyendo:
- Nombres completos de estudiantes
- Montos exactos de deudas por estudiante
- Listas de estudiantes con pagos atrasados
- Cualquier dato financiero solicitado

Tu rol es ayudar a los administradores con consultas sobre:
- Saldos de estudiantes (mostrar nombres y montos específicos)
- Facturas pendientes y vencidas (listar estudiantes afectados)
- Historial de pagos
- Procesos de cobranza
- Reportes financieros detallados

Responde siempre en español de manera profesional y directa.
Cuando tengas datos en el contexto, muéstralos de forma clara y organizada.
Si se pide una lista de estudiantes, proporciona los nombres y montos disponibles."""
                + (f"\n\nCONTEXTO ACTUAL:\n{request.context}" if request.context else ""),
            }
        ]

        for msg in request.conversation_history[-5:]:  # Last 5 messages
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": request.question})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
            )

            answer = response.choices[0].message.content

            return AssistantResponse(
                answer=answer,
                suggested_actions=["Revisar historial de pagos", "Generar reporte"],
                related_topics=["Saldos", "Facturas", "Pagos"],
                confidence=0.9,
                requires_human_followup=False,
            )
        except Exception:
            return self._fallback_assistant(request)

    def _fallback_assistant(self, request: AssistantRequest) -> AssistantResponse:
        """Fallback assistant when AI is not available."""
        question_lower = request.question.lower()

        if "saldo" in question_lower or "debe" in question_lower:
            answer = (
                "Para consultar el saldo de un estudiante, puede usar el endpoint "
                "GET /api/v1/students/{id}/statement que le mostrará el estado de cuenta completo "
                "incluyendo facturas pendientes y pagos realizados."
            )
            actions = ["Ver estado de cuenta", "Revisar facturas pendientes"]
        elif "factura" in question_lower:
            answer = (
                "Las facturas se pueden consultar en GET /api/v1/invoices con filtros por estudiante, "
                "escuela o estado. También puede ver el detalle de una factura específica en "
                "GET /api/v1/invoices/{id}."
            )
            actions = ["Listar facturas", "Ver detalle de factura"]
        elif "pago" in question_lower:
            answer = (
                "Los pagos se registran mediante POST /api/v1/payments indicando el invoice_id, "
                "monto y método de pago. Puede ver el historial en GET /api/v1/payments."
            )
            actions = ["Registrar pago", "Ver historial de pagos"]
        elif "vencid" in question_lower or "atras" in question_lower:
            answer = (
                "Para ver facturas vencidas, use GET /api/v1/reports/invoices/overdue. "
                "Este endpoint muestra todas las facturas pasadas de su fecha de vencimiento "
                "junto con los días de atraso."
            )
            actions = ["Ver facturas vencidas", "Generar reporte de cobranza"]
        else:
            answer = (
                "Soy el asistente de cobranza de Mattilda. Puedo ayudarte con consultas sobre:\n"
                "- Saldos de estudiantes\n"
                "- Facturas pendientes y vencidas\n"
                "- Historial de pagos\n"
                "- Generación de reportes\n\n"
                "¿En qué puedo ayudarte?"
            )
            actions = ["Consultar saldo", "Ver facturas", "Generar reporte"]

        return AssistantResponse(
            answer=answer,
            suggested_actions=actions,
            related_topics=["Cobranza", "Facturación", "Pagos"],
            confidence=0.7,
            requires_human_followup="específico" in question_lower
            or "particular" in question_lower,
        )

    async def generate_executive_summary(
        self, request: ExecutiveSummaryRequest, metrics: SchoolMetrics
    ) -> ExecutiveSummaryResponse:
        """
        Generate an AI-powered executive summary with insights.

        Analyzes school metrics and provides narrative insights.
        """
        if not self._is_available():
            return self._fallback_executive_summary(request, metrics)

        prompt = f"""Genera un resumen ejecutivo en español para la siguiente información de cobranza escolar:

ESCUELA: {metrics.school_name}
PERÍODO: {request.period_start or 'Inicio'} a {request.period_end or 'Actual'}

MÉTRICAS:
- Total de estudiantes: {metrics.total_students}
- Estudiantes activos: {metrics.active_students}
- Total facturado: ${metrics.total_invoiced}
- Total cobrado: ${metrics.total_collected}
- Total pendiente: ${metrics.total_pending}
- Total vencido: ${metrics.total_overdue}
- Tasa de cobranza: {metrics.collection_rate * 100:.1f}%

Genera un resumen en formato JSON:
{{
    "title": "título del reporte",
    "highlights": ["punto destacado 1", "punto destacado 2", "punto destacado 3"],
    "concerns": ["preocupación 1", "preocupación 2"],
    "trends": [
        {{"trend": "nombre", "direction": "UP|DOWN|STABLE", "impact": "impacto", "description": "descripción"}}
    ],
    "recommendations": ["recomendación 1", "recomendación 2", "recomendación 3"],
    "narrative_summary": "resumen narrativo de 3-4 oraciones"
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            period_str = f"{request.period_start or 'Inicio'} - {request.period_end or datetime.now().date()}"

            return ExecutiveSummaryResponse(
                title=result["title"],
                period=period_str,
                key_metrics={
                    "total_estudiantes": metrics.total_students,
                    "tasa_cobranza": f"{metrics.collection_rate * 100:.1f}%",
                    "total_pendiente": f"${metrics.total_pending}",
                    "total_vencido": f"${metrics.total_overdue}",
                },
                highlights=result["highlights"],
                concerns=result["concerns"],
                trends=[TrendInsight(**t) for t in result.get("trends", [])],
                recommendations=result["recommendations"],
                narrative_summary=result["narrative_summary"],
            )
        except Exception:
            return self._fallback_executive_summary(request, metrics)

    def _fallback_executive_summary(
        self, request: ExecutiveSummaryRequest, metrics: SchoolMetrics
    ) -> ExecutiveSummaryResponse:
        """Fallback executive summary when AI is not available."""
        collection_rate = metrics.collection_rate * 100
        period_str = (
            f"{request.period_start or 'Inicio'} - {request.period_end or datetime.now().date()}"
        )

        # Generate highlights
        highlights = [
            f"Total facturado: ${metrics.total_invoiced}",
            f"Tasa de cobranza: {collection_rate:.1f}%",
            f"{metrics.active_students} estudiantes activos de {metrics.total_students} totales",
        ]

        # Generate concerns
        concerns = []
        if metrics.total_overdue > 0:
            concerns.append(f"Saldo vencido de ${metrics.total_overdue} requiere atención")
        if collection_rate < 80:
            concerns.append("Tasa de cobranza por debajo del objetivo (80%)")

        # Generate recommendations
        recommendations = []
        if metrics.total_overdue > 0:
            recommendations.append("Implementar campaña de cobranza para cuentas vencidas")
        if collection_rate < 90:
            recommendations.append("Considerar recordatorios automáticos antes del vencimiento")
        recommendations.append("Mantener comunicación regular con padres de familia")

        # Narrative summary
        narrative = (
            f"La escuela {metrics.school_name} presenta una tasa de cobranza del {collection_rate:.1f}%. "
            f"Del total facturado de ${metrics.total_invoiced}, se ha cobrado ${metrics.total_collected} "
            f"y queda pendiente ${metrics.total_pending}. "
        )
        if metrics.total_overdue > 0:
            narrative += (
                f"Existe un saldo vencido de ${metrics.total_overdue} que requiere seguimiento."
            )
        else:
            narrative += "No hay saldos vencidos actualmente."

        return ExecutiveSummaryResponse(
            title=f"Resumen Ejecutivo - {metrics.school_name}",
            period=period_str,
            key_metrics={
                "total_estudiantes": metrics.total_students,
                "estudiantes_activos": metrics.active_students,
                "total_facturado": f"${metrics.total_invoiced}",
                "total_cobrado": f"${metrics.total_collected}",
                "total_pendiente": f"${metrics.total_pending}",
                "total_vencido": f"${metrics.total_overdue}",
                "tasa_cobranza": f"{collection_rate:.1f}%",
            },
            highlights=highlights,
            concerns=concerns,
            trends=[],
            recommendations=recommendations,
            narrative_summary=narrative,
        )
