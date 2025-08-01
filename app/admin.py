import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


from datetime import datetime
from db import (
    get_all_users_with_chats,
    get_user_chat_sessions,
    load_messages,
    # User-specific analytics functions
    get_user_total_images_created,
    get_user_images_created_over_time,
    get_user_activity_over_time,
    get_user_messages_over_time,
    get_user_message_distribution,
    get_user_hourly_breakdown,
    get_user_session_length_stats,
    get_user_total_messages,
    get_user_total_sessions,
    get_user_last_activity,
    export_user_chat_data,
)

from io import BytesIO
from PIL import Image as PILImage
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER


def process_local_image(
    image_path: str, max_width: float = 4 * inch, max_height: float = 3 * inch
) -> tuple[BytesIO | None, int, int]:
    """Process a local image file for PDF inclusion."""
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            return None, 0, 0

        # Open the local image file with PIL
        pil_image = PILImage.open(image_path)

        # Convert to RGB if necessary (for RGBA or other formats)
        if pil_image.mode in ("RGBA", "LA", "P"):
            pil_image = pil_image.convert("RGB")

        # Calculate scaling to fit within max dimensions while maintaining aspect ratio
        width, height = pil_image.size
        width_ratio = max_width / width
        height_ratio = max_height / height
        scale_ratio = min(width_ratio, height_ratio, 1.0)  # Don't upscale

        new_width = int(width * scale_ratio)
        new_height = int(height * scale_ratio)

        # Resize if needed
        if scale_ratio < 1.0:
            pil_image = pil_image.resize(
                (new_width, new_height), PILImage.Resampling.LANCZOS
            )

        # Save to BytesIO as JPEG
        img_buffer = BytesIO()
        pil_image.save(img_buffer, format="JPEG", quality=85)
        img_buffer.seek(0)

        return img_buffer, new_width, new_height

    except Exception:
        # Return None to indicate failure
        return None, 0, 0


def generate_chat_pdf(user_id: str) -> BytesIO:
    """Generate a PDF report of all chat sessions for a user."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
    )
    session_style = ParagraphStyle(
        "SessionStyle",
        parent=styles["Heading3"],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=15,
        textColor=colors.darkblue,
    )
    user_msg_style = ParagraphStyle(
        "UserMessage",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=8,
        leftIndent=20,
        textColor=colors.darkgreen,
    )
    ai_msg_style = ParagraphStyle(
        "AIMessage",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=8,
        leftIndent=40,
        textColor=colors.darkred,
    )

    # Build story (content)
    story = []

    # Title page
    story.append(Paragraph("Chat History Report", title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"<b>User:</b> {user_id}", styles["Normal"]))
    story.append(
        Paragraph(
            f"<b>Generated on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 30))

    # Get user stats
    total_messages = get_user_total_messages(user_id)
    total_sessions = get_user_total_sessions(user_id)
    total_images = get_user_total_images_created(user_id)
    last_activity = get_user_last_activity(user_id)

    # Summary section
    story.append(Paragraph("Summary", heading_style))
    summary_data = [
        ["Total Messages:", str(total_messages)],
        ["Total Sessions:", str(total_sessions)],
        ["Images Generated:", str(total_images)],
        ["Last Activity:", last_activity if last_activity != "Never" else "Never"],
    ]
    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(summary_table)
    story.append(PageBreak())

    # Get all sessions
    user_sessions = get_user_chat_sessions(user_id)

    if not user_sessions:
        story.append(
            Paragraph("No chat sessions found for this user.", styles["Normal"])
        )
    else:
        story.append(Paragraph("Chat Sessions", heading_style))

        for i, (session_id, snippet, msg_count, last_activity) in enumerate(
            user_sessions, 1
        ):
            # Session header
            try:
                activity_date = datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
                formatted_date = activity_date.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_date = "Unknown"

            session_title = f"Session {i}: {formatted_date}"
            story.append(Paragraph(session_title, session_style))
            story.append(
                Paragraph(
                    f"<i>Messages: {msg_count} | Preview: {snippet}</i>",
                    styles["Italic"],
                )
            )
            story.append(Spacer(1, 10))

            # Get messages for this session
            messages = load_messages(user_id, session_id)

            if messages:
                for msg in messages:
                    role_prefix = "👤 User:" if msg["role"] == "user" else "🤖 AI:"
                    content = msg["content"]

                    if msg["type"] == "text":
                        # Truncate very long messages
                        if len(content) > 500:
                            content = content[:500] + "... [truncated]"

                        # Escape HTML characters
                        content = (
                            content.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )

                        message_text = f"<b>{role_prefix}</b> {content}"

                        if msg["role"] == "user":
                            story.append(Paragraph(message_text, user_msg_style))
                        else:
                            story.append(Paragraph(message_text, ai_msg_style))

                    else:
                        # Handle image messages
                        # Add text description first
                        message_text = f"<b>{role_prefix}</b> [Image] {content}"

                        if msg["role"] == "user":
                            story.append(Paragraph(message_text, user_msg_style))
                        else:
                            story.append(Paragraph(message_text, ai_msg_style))

                        # Try to add the actual image
                        if msg.get("url"):
                            img_buffer, img_width, img_height = process_local_image(
                                msg["url"]
                            )
                            if img_buffer:  # If image was successfully processed
                                try:
                                    pdf_image = Image(
                                        img_buffer, width=img_width, height=img_height
                                    )
                                    story.append(Spacer(1, 6))
                                    story.append(pdf_image)
                                    story.append(Spacer(1, 6))
                                except Exception:
                                    # If image fails to add to PDF, just note it
                                    story.append(
                                        Paragraph(
                                            "<i>[Image could not be displayed]</i>",
                                            styles["Italic"],
                                        )
                                    )
                            else:
                                story.append(
                                    Paragraph(
                                        "<i>[Image could not be loaded]</i>",
                                        styles["Italic"],
                                    )
                                )

            story.append(Spacer(1, 20))

            # Add page break between sessions (except for the last one)
            if i < len(user_sessions):
                story.append(PageBreak())

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def show_admin_portal():
    # Check if current user is admin
    def is_admin(user_email: str) -> bool:
        """Check if the current user is an admin based on email."""
        admin_emails = st.secrets.get("admin_emails", [])
        return user_email in admin_emails

    # Admin authentication check
    user = st.experimental_user
    if not user.is_logged_in:
        st.error("Please log in to access the admin portal.")
        st.stop()

    user_email = user["email"]
    if not is_admin(user_email):
        st.error("Access denied. You don't have admin privileges.")
        st.stop()

    st.set_page_config(
        page_title="Admin Portal - Origami AI",
        page_icon="🔐",
        layout="wide",
    )

    # Sidebar with navigation
    with st.sidebar:
        st.logo(image="static/origami_icon.png", size="large")
        st.subheader("Admin Panel")
        st.text(f"Logged in as: {user_email}")

        if st.button("🏠 Back to App", use_container_width=True, type="primary"):
            st.query_params = {}
            st.rerun()

        if st.button("Logout", icon=":material/logout:", use_container_width=True):
            st.logout()

    st.title("Admin Portal", anchor=False)
    st.caption(f"Welcome, {user_email}")

    # Create tabs for different admin functions
    tab1, tab2 = st.tabs(["📊 Analytics Dashboard", "💬 User Chat Histories"])

    with tab1:
        st.header("📈 User-Specific Analytics Dashboard")

        # Get all users with chat data for the selector
        users_with_chats = get_all_users_with_chats()

        if not users_with_chats:
            st.error("No users with chat data found.")
            return

        # User selector
        user_options = [
            (user_id, f"{user_id} ({msg_count} msgs)")
            for user_id, msg_count, _ in users_with_chats
        ]
        selected_user_display = st.selectbox(
            "🔍 Select user to analyze:",
            options=[display for _, display in user_options],
            key="analytics_user_selector",
        )

        # Get the actual user_id from the selection
        selected_user = None
        for user_id, display in user_options:
            if display == selected_user_display:
                selected_user = user_id
                break

        if not selected_user:
            st.error("Please select a valid user.")
            return

        st.info(f"📊 Showing analytics for: **{selected_user}**")
        st.divider()

        # === KPI METRICS ===
        col1, col2, col3, col4 = st.columns(4)

        total_images = get_user_total_images_created(selected_user)
        total_messages = get_user_total_messages(selected_user)
        total_sessions = get_user_total_sessions(selected_user)
        last_activity = get_user_last_activity(selected_user)

        with col1:
            st.metric("🎨 Images Created", f"{total_images:,}")
        with col2:
            st.metric("💬 Total Messages", f"{total_messages:,}")
        with col3:
            st.metric("📱 Total Sessions", f"{total_sessions:,}")
        with col4:
            try:
                if last_activity != "Never":
                    activity_date = datetime.strptime(
                        last_activity, "%Y-%m-%d %H:%M:%S"
                    )
                    formatted_date = activity_date.strftime("%m/%d/%Y")
                else:
                    formatted_date = "Never"
            except:
                formatted_date = "Unknown"
            st.metric("📅 Last Active", formatted_date)

        st.divider()

        # === USER ENGAGEMENT ANALYSIS ===
        st.subheader("🎯 User Engagement Analysis")

        # Calculate engagement metrics
        avg_messages_per_session = (
            total_messages / total_sessions if total_sessions > 0 else 0
        )

        # Get session lengths to calculate engagement depth
        session_stats = get_user_session_length_stats(selected_user)
        if session_stats:
            _, msg_counts, durations = zip(*session_stats)
            avg_session_duration = sum(durations) / len(durations)
            total_duration = sum(durations)
        else:
            avg_session_duration = 0
            total_duration = 0

        # Get daily activity to calculate consistency
        daily_activity = get_user_activity_over_time(selected_user)
        active_days = len(daily_activity) if daily_activity else 0

        # Format total duration for display
        if total_duration >= 60:
            duration_display = f"{total_duration / 60:.1f} hrs"
        else:
            duration_display = f"{total_duration} min"

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📊 Avg Msgs/Session", f"{avg_messages_per_session:.1f}")
        with col2:
            st.metric("⏱️ Avg Session Duration", f"{avg_session_duration:.1f} min")
        with col3:
            st.metric("📅 Active Days", f"{active_days}")
        with col4:
            st.metric("⏰ Total Duration", duration_display)

        # Engagement depth chart
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Engagement Intensity**")
            if daily_activity:
                dates, daily_counts = zip(*daily_activity)
                avg_daily_messages = sum(daily_counts) / len(daily_counts)

                # Categorize engagement levels
                high_engagement_days = len(
                    [c for c in daily_counts if c >= avg_daily_messages * 1.5]
                )
                medium_engagement_days = len(
                    [
                        c
                        for c in daily_counts
                        if avg_daily_messages <= c < avg_daily_messages * 1.5
                    ]
                )
                low_engagement_days = len(
                    [c for c in daily_counts if c < avg_daily_messages]
                )

                engagement_data = [
                    high_engagement_days,
                    medium_engagement_days,
                    low_engagement_days,
                ]
                engagement_labels = [
                    f"High Activity (≥{avg_daily_messages * 1.5:.1f} msgs/day)",
                    f"Medium Activity ({avg_daily_messages:.1f}-{avg_daily_messages * 1.5:.1f} msgs/day)",
                    f"Low Activity (<{avg_daily_messages:.1f} msgs/day)",
                ]

                if sum(engagement_data) > 0:
                    fig_engagement = px.pie(
                        values=engagement_data,
                        names=engagement_labels,
                        title="Daily Engagement Distribution",
                        color_discrete_sequence=["#174C4F", "#F0EB4E", "#CCCCCC"],
                    )
                    fig_engagement.update_layout(height=300)
                    st.plotly_chart(fig_engagement, use_container_width=True)
                else:
                    st.info("No engagement data available.")
            else:
                st.info("No daily activity data available.")

        with col2:
            st.write("**Session Length Distribution**")
            if session_stats and len(session_stats) > 1:
                _, msg_counts, durations = zip(*session_stats)

                # Create session length categories
                short_sessions = len([c for c in msg_counts if c <= 5])
                medium_sessions = len([c for c in msg_counts if 5 < c <= 15])
                long_sessions = len([c for c in msg_counts if c > 15])

                session_data = [short_sessions, medium_sessions, long_sessions]
                session_labels = [
                    "Short (≤5 msgs)",
                    "Medium (6-15 msgs)",
                    "Long (>15 msgs)",
                ]

                fig_sessions = px.pie(
                    values=session_data,
                    names=session_labels,
                    title="Session Length Categories",
                    color_discrete_sequence=["#FFCCCB", "#F0EB4E", "#174C4F"],
                )
                fig_sessions.update_layout(height=300)
                st.plotly_chart(fig_sessions, use_container_width=True)
            else:
                st.info("Insufficient session data for analysis.")

        st.divider()

        # === ACTIVITY TRENDS ===
        st.subheader("📊 User Activity Trends")
        col1, col2 = st.columns(2)

        with col1:
            # User messages vs total activity over time
            user_messages_data = get_user_messages_over_time(selected_user)
            total_activity_data = get_user_activity_over_time(selected_user)

            if user_messages_data and total_activity_data:
                # Create combined chart showing user messages vs total activity
                user_dates, user_counts = zip(*user_messages_data)
                total_dates, total_counts = zip(*total_activity_data)

                fig_activity = go.Figure()

                fig_activity.add_trace(
                    go.Scatter(
                        x=user_dates,
                        y=user_counts,
                        mode="lines+markers",
                        name="User Messages",
                        line=dict(color="#174C4F", width=3),
                        marker=dict(size=8, color="#174C4F"),
                    )
                )

                fig_activity.add_trace(
                    go.Scatter(
                        x=total_dates,
                        y=total_counts,
                        mode="lines+markers",
                        name="Total Activity",
                        line=dict(color="#F0EB4E", width=3),
                        marker=dict(size=8, color="#F0EB4E"),
                    )
                )

                fig_activity.update_layout(
                    title="Daily Activity: User Messages vs Total",
                    xaxis_title="Date",
                    yaxis_title="Message Count",
                    height=400,
                    xaxis=dict(tickformat="%m/%d", tickangle=45),
                )
                st.plotly_chart(fig_activity, use_container_width=True)
            else:
                st.info("No activity data available for this user.")

        with col2:
            # Images created over time
            images_data = get_user_images_created_over_time(selected_user)
            if images_data:
                dates, counts = zip(*images_data)
                fig_images = px.line(
                    x=dates,
                    y=counts,
                    labels={"x": "Date", "y": "Images Created"},
                    title="AI Images Generated Daily",
                    color_discrete_sequence=["#F0EB4E"],
                )
                fig_images.update_layout(height=400)
                st.plotly_chart(fig_images, use_container_width=True)
            else:
                st.info("No image generation data available for this user.")

        # === MESSAGE DISTRIBUTION ===
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💬 Message Type Distribution")
            message_dist = get_user_message_distribution(selected_user)
            if message_dist:
                types, counts = zip(*message_dist)
                fig_messages = px.pie(
                    values=counts,
                    names=types,
                    title="User Activity Breakdown",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig_messages.update_layout(height=400)
                st.plotly_chart(fig_messages, use_container_width=True)
            else:
                st.info("No message data available for this user.")

        with col2:
            st.subheader("🕐 Hourly Activity Pattern")
            hourly_breakdown = get_user_hourly_breakdown(selected_user)
            if hourly_breakdown:
                hours, user_counts, ai_counts = zip(*hourly_breakdown)

                fig_hourly = go.Figure()

                fig_hourly.add_trace(
                    go.Bar(
                        x=hours,
                        y=user_counts,
                        name="User Messages",
                        marker_color="#174C4F",
                    )
                )

                fig_hourly.add_trace(
                    go.Bar(
                        x=hours,
                        y=ai_counts,
                        name="AI Responses",
                        marker_color="#F0EB4E",
                    )
                )

                fig_hourly.update_layout(
                    title="Peak Usage Hours (User vs AI)",
                    xaxis_title="Hour of Day",
                    yaxis_title="Message Count",
                    barmode="stack",
                    height=400,
                    xaxis=dict(tickmode="linear", tick0=0, dtick=1),
                )
                st.plotly_chart(fig_hourly, use_container_width=True)
            else:
                st.info("No hourly activity data available for this user.")

        # === SESSION ANALYSIS ===
        st.subheader("📈 User Session Analysis")

        session_stats = get_user_session_length_stats(selected_user)
        if session_stats:
            col1, col2 = st.columns(2)

            with col1:
                # Session length distribution
                _, msg_counts, durations = zip(*session_stats)

                fig_duration = px.scatter(
                    x=msg_counts,
                    y=durations,
                    labels={"x": "Messages in Session", "y": "Duration (minutes)"},
                    title="Session Duration vs Message Count",
                    color_discrete_sequence=["#174C4F"],
                )
                fig_duration.update_layout(height=400)
                st.plotly_chart(fig_duration, use_container_width=True)

            with col2:
                # Average session metrics
                avg_duration = sum(durations) / len(durations)
                avg_messages = sum(msg_counts) / len(msg_counts)
                longest_session = max(msg_counts)
                longest_duration = max(durations)

                st.metric("⏱️ Avg Session Duration", f"{avg_duration:.1f} min")
                st.metric("💬 Avg Messages per Session", f"{avg_messages:.1f}")
                st.metric("🏆 Longest Session", f"{longest_session} messages")
                st.metric("⏰ Max Duration", f"{longest_duration} min")
        else:
            st.info("No session data available for this user.")

    with tab2:
        st.subheader("User Chat Histories")

        # Get all users with chat data
        users_with_chats = get_all_users_with_chats()

        if not users_with_chats:
            st.info("No users with chat histories found.")
        else:
            # Search functionality
            search_term = st.text_input(
                "🔍 Search users by email:", placeholder="Enter user email..."
            )

            # Filter users based on search
            filtered_users = users_with_chats
            if search_term:
                filtered_users = [
                    (user_id, msg_count, last_activity)
                    for user_id, msg_count, last_activity in users_with_chats
                    if search_term.lower() in user_id.lower()
                ]

            if not filtered_users:
                st.warning("No users found matching your search.")
            else:
                st.write(f"Found **{len(filtered_users)}** users with chat histories")

                # Create two columns: user list and chat display
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.subheader("Users")
                    selected_user = None

                    for user_id, msg_count, last_activity in filtered_users:
                        # Format the last activity date
                        try:
                            activity_date = datetime.strptime(
                                last_activity, "%Y-%m-%d %H:%M:%S"
                            )
                            formatted_date = activity_date.strftime("%m/%d/%Y")
                        except:
                            formatted_date = "N/A"

                        # Create a button for each user
                        user_label = f"📧 {user_id}\n💬 {msg_count} messages\n📅 {formatted_date}"
                        if st.button(
                            user_label, key=f"user_{user_id}", use_container_width=True
                        ):
                            selected_user = user_id
                            st.session_state.selected_admin_user = user_id

                    # Get selected user from session state
                    if "selected_admin_user" in st.session_state:
                        selected_user = st.session_state.selected_admin_user

                with col2:
                    st.subheader("Chat History")

                    if selected_user:
                        col_header, col_download = st.columns([3, 1])
                        with col_header:
                            st.write(f"**Viewing chats for:** {selected_user}")

                        with col_download:
                            # Download button for user's chat data as PDF
                            try:
                                # Check if user has any chat data
                                user_sessions = get_user_chat_sessions(selected_user)
                                if user_sessions:
                                    # Generate PDF
                                    pdf_buffer = generate_chat_pdf(selected_user)

                                    # Generate filename with timestamp
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    filename = f"chat_report_{selected_user.replace('@', '_at_').replace('.', '_')}_{timestamp}.pdf"

                                    st.download_button(
                                        label="📄 Download PDF",
                                        data=pdf_buffer.getvalue(),
                                        file_name=filename,
                                        mime="application/pdf",
                                        help="Download complete chat history as PDF report",
                                        use_container_width=True,
                                    )
                                else:
                                    st.button(
                                        "📄 Download PDF",
                                        disabled=True,
                                        help="No chat data available",
                                        use_container_width=True,
                                    )
                            except Exception as e:
                                st.error(f"Error generating PDF: {str(e)}")

                        # Get user's chat sessions
                        user_sessions = get_user_chat_sessions(selected_user)

                        if not user_sessions:
                            st.info("No chat sessions found for this user.")
                        else:
                            # Session selector
                            session_options = []
                            for (
                                session_id,
                                snippet,
                                msg_count,
                                last_activity,
                            ) in user_sessions:
                                try:
                                    activity_date = datetime.strptime(
                                        last_activity, "%Y-%m-%d %H:%M:%S"
                                    )
                                    formatted_date = activity_date.strftime(
                                        "%m/%d/%Y %H:%M"
                                    )
                                except:
                                    formatted_date = "N/A"

                                session_label = (
                                    f"{formatted_date} - {snippet} ({msg_count} msgs)"
                                )
                                session_options.append((session_label, session_id))

                            if session_options:
                                selected_session_label = st.selectbox(
                                    "Select a chat session:",
                                    options=[label for label, _ in session_options],
                                    key="admin_session_selector",
                                )

                                # Find the selected session ID
                                selected_session_id = None
                                for label, session_id in session_options:
                                    if label == selected_session_label:
                                        selected_session_id = session_id
                                        break

                                if selected_session_id:
                                    st.divider()

                                    # Load and display messages for the selected session
                                    messages = load_messages(
                                        selected_user, selected_session_id
                                    )

                                    if not messages:
                                        st.info("No messages found in this session.")
                                    else:
                                        st.write(f"**Session:** {selected_session_id}")
                                        st.write(f"**Total messages:** {len(messages)}")
                                        st.divider()

                                        # Display messages
                                        for i, msg in enumerate(messages):
                                            role_emoji = (
                                                "👤" if msg["role"] == "user" else "🤖"
                                            )
                                            role_color = (
                                                "blue"
                                                if msg["role"] == "user"
                                                else "green"
                                            )

                                            with st.container():
                                                st.markdown(
                                                    f"**{role_emoji} {msg['role'].title()}:**"
                                                )

                                                if msg["type"] == "text":
                                                    st.markdown(
                                                        f":{role_color}[{msg['content']}]"
                                                    )
                                                else:
                                                    st.markdown(
                                                        f":{role_color}[Image: {msg['content']}]"
                                                    )
                                                    if msg.get("url"):
                                                        st.image(
                                                            msg["url"],
                                                            caption=msg["content"],
                                                            width=300,
                                                        )

                                                st.write("")  # Add spacing
                    else:
                        st.info(
                            "👈 Select a user from the list to view their chat history."
                        )
