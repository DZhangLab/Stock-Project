package com.summer.stockproject.login.Entity;

import javax.persistence.Column;
import javax.persistence.Embeddable;
import javax.persistence.JoinColumn;
import javax.persistence.ManyToOne;
import java.io.Serializable;
import java.util.Objects;

@Embeddable
public class userrole implements Serializable {
//    @ManyToOne(targetEntity = User.class)
//    @JoinColumn(name = "useremail")
    @Column(name = "useremail")
    private String useremail;

    @Column(name = "role", nullable = false)
    private String role;

    public userrole() {

    }

    public userrole(String useremail, String role) {
        this.useremail = useremail;
        this.role = role;
    }

    public String getUseremail() {
        return useremail;
    }

    public void setUseremail(String useremail) {
        this.useremail = useremail;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    @Override
    public String toString() {
        return "userrole{" +
                "useremail='" + useremail + '\'' +
                ", role='" + role + '\'' +
                '}';
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        userrole userrole = (userrole) o;
        return Objects.equals(useremail, userrole.useremail) && Objects.equals(role, userrole.role);
    }

    @Override
    public int hashCode() {
        return Objects.hash(useremail, role);
    }
}
