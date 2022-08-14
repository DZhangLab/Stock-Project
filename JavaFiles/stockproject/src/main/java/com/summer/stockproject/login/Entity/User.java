package com.summer.stockproject.login.Entity;

import javax.persistence.*;
import java.util.List;
import java.util.Set;

@Entity
@Table(name="user")
public class User  {

    @Id
    @Column(name="email")
    private String email;

    @Column(name="firstname")
    private String firstname;

    @Column(name="lastname")
    private String lastname;

    @Column(name="phone")
    private int phone;

    @Column(name="password")
    private String password;

    @Column(name="salt")
    private String saltt;

    @OneToMany(mappedBy = "userrole.useremail" , cascade =  CascadeType.ALL, fetch = FetchType.EAGER)
    private Set<Role> roles;

    public Set<Role> getRoles() {
        return roles;
    }
//
    public void setRoles(Set<Role> roles) {
        this.roles = roles;
    }

    public User() {

    }

    public User(String email, String firstname, String lastname, int phone, String password, String saltt) {
        this.email = email;
        this.firstname = firstname;
        this.lastname = lastname;
        this.phone = phone;
        this.password = password;
        this.saltt = saltt;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getFirstname() {
        return firstname;
    }

    public void setFirstname(String firstname) {
        this.firstname = firstname;
    }

    public String getLastname() {
        return lastname;
    }

    public void setLastname(String lastname) {
        this.lastname = lastname;
    }

    public int getPhone() {
        return phone;
    }

    public void setPhone(int phone) {
        this.phone = phone;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public String getSaltt() {
        return saltt;
    }

    public void setSaltt(String saltt) {
        this.saltt = saltt;
    }

    @Override
    public String toString() {
        return "User{" +
                "email='" + email + '\'' +
                ", firstname='" + firstname + '\'' +
                ", lastname='" + lastname + '\'' +
                ", phone=" + phone +
                ", password='" + password + '\'' +
                ", saltt='" + saltt + '\'' +
                ", roles=" + roles +
                '}';
    }
}
